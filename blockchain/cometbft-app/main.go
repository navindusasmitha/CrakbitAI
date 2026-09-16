package main

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	abciserver "github.com/cometbft/cometbft/abci/server"
	abci "github.com/cometbft/cometbft/abci/types"
)

const bridgeVersion = "crakbit-cometbft-bridge/0.17"

type executionClient struct {
	baseURL string
	token   string
	http    *http.Client
}

type bridgeApp struct {
	abci.BaseApplication
	execution executionClient
}

type infoResponse struct {
	Protocol        string `json:"protocol"`
	ChainID         string `json:"chain_id"`
	Height          int64  `json:"height"`
	ApplicationHash string `json:"application_hash"`
}

type checkResponse struct {
	Accepted bool   `json:"accepted"`
	TxID     string `json:"txid"`
	Error    string `json:"error"`
	Detail   string `json:"detail"`
}

type finalizeResponse struct {
	Protocol            string `json:"protocol"`
	Height              int64  `json:"height"`
	NextApplicationHash string `json:"next_application_hash"`
	RequestHash         string `json:"request_hash"`
	TransactionCount    int    `json:"transaction_count"`
}

type commitResponse struct {
	Protocol        string `json:"protocol"`
	Height          int64  `json:"height"`
	ApplicationHash string `json:"application_hash"`
	Committed       bool   `json:"committed"`
}

type txEnvelope struct {
	Transaction json.RawMessage `json:"transaction"`
}

type finalizeEnvelope struct {
	Height             int64             `json:"height"`
	ConsensusBlockHash string            `json:"consensus_block_hash"`
	Transactions       []json.RawMessage `json:"transactions"`
}

type snapshotDescriptor struct {
	Height         uint64 `json:"height"`
	Format         uint32 `json:"format"`
	Chunks         uint32 `json:"chunks"`
	HashHex        string `json:"hash_hex"`
	MetadataBase64 string `json:"metadata_base64"`
}

type snapshotListResponse struct {
	Snapshots []snapshotDescriptor `json:"snapshots"`
}

type snapshotOfferEnvelope struct {
	Height         uint64 `json:"height"`
	Format         uint32 `json:"format"`
	Chunks         uint32 `json:"chunks"`
	HashHex        string `json:"hash_hex"`
	MetadataBase64 string `json:"metadata_base64"`
	AppHashHex     string `json:"app_hash_hex"`
}

type snapshotOfferResponse struct {
	Result string `json:"result"`
	Reason string `json:"reason"`
}

type snapshotChunkResponse struct {
	ChunkBase64 string `json:"chunk_base64"`
}

type snapshotApplyEnvelope struct {
	Index       uint32 `json:"index"`
	ChunkBase64 string `json:"chunk_base64"`
	Sender      string `json:"sender"`
}

type snapshotApplyResponse struct {
	Result        string   `json:"result"`
	RefetchChunks []uint32 `json:"refetch_chunks"`
	RejectSenders []string `json:"reject_senders"`
}

func newBridge(baseURL, token string) *bridgeApp {
	return &bridgeApp{
		execution: executionClient{
			baseURL: strings.TrimRight(baseURL, "/"),
			token:   token,
			http:    &http.Client{Timeout: 30 * time.Second},
		},
	}
}

func (c executionClient) doJSON(ctx context.Context, method, path string, input any, output any) error {
	var body bytes.Buffer
	if input != nil {
		if err := json.NewEncoder(&body).Encode(input); err != nil {
			return err
		}
	}
	req, err := http.NewRequestWithContext(ctx, method, c.baseURL+path, &body)
	if err != nil {
		return err
	}
	req.Header.Set("Authorization", "Bearer "+c.token)
	if input != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	resp, err := c.http.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		var failure struct {
			Detail any `json:"detail"`
		}
		_ = json.NewDecoder(resp.Body).Decode(&failure)
		return fmt.Errorf("execution service %s %s returned %d: %v", method, path, resp.StatusCode, failure.Detail)
	}
	if output == nil {
		return nil
	}
	return json.NewDecoder(resp.Body).Decode(output)
}

func decodeHash(value string) ([]byte, error) {
	if len(value) != 64 {
		return nil, fmt.Errorf("expected 64-character application hash, got %d", len(value))
	}
	decoded, err := hex.DecodeString(value)
	if err != nil {
		return nil, fmt.Errorf("decode application hash: %w", err)
	}
	return decoded, nil
}

func rawTransactions(txs [][]byte) ([]json.RawMessage, error) {
	items := make([]json.RawMessage, 0, len(txs))
	for _, tx := range txs {
		if !json.Valid(tx) {
			return nil, errors.New("Crakbit transaction must be canonical JSON for the ABCI bridge")
		}
		items = append(items, json.RawMessage(append([]byte(nil), tx...)))
	}
	return items, nil
}

func (app *bridgeApp) Info(ctx context.Context, _ *abci.RequestInfo) (*abci.ResponseInfo, error) {
	var info infoResponse
	if err := app.execution.doJSON(ctx, http.MethodGet, "/v2/info", nil, &info); err != nil {
		return nil, err
	}
	appHash, err := decodeHash(info.ApplicationHash)
	if err != nil {
		return nil, err
	}
	return &abci.ResponseInfo{
		Data:             bridgeVersion,
		Version:          bridgeVersion,
		AppVersion:       2,
		LastBlockHeight:  info.Height,
		LastBlockAppHash: appHash,
	}, nil
}

func (app *bridgeApp) CheckTx(ctx context.Context, req *abci.RequestCheckTx) (*abci.ResponseCheckTx, error) {
	if !json.Valid(req.Tx) {
		return &abci.ResponseCheckTx{Code: 1, Log: "transaction is not valid JSON"}, nil
	}
	var result checkResponse
	if err := app.execution.doJSON(
		ctx,
		http.MethodPost,
		"/v2/check-tx",
		txEnvelope{Transaction: json.RawMessage(req.Tx)},
		&result,
	); err != nil {
		return nil, err
	}
	if !result.Accepted {
		return &abci.ResponseCheckTx{Code: 1, Log: result.Error + ": " + result.Detail}, nil
	}
	return &abci.ResponseCheckTx{Code: abci.CodeTypeOK, Log: result.TxID}, nil
}

func (app *bridgeApp) PrepareProposal(ctx context.Context, req *abci.RequestPrepareProposal) (*abci.ResponsePrepareProposal, error) {
	selected := make([][]byte, 0, len(req.Txs))
	var total int64
	for _, tx := range req.Txs {
		response, err := app.CheckTx(ctx, &abci.RequestCheckTx{Tx: tx})
		if err != nil {
			return nil, err
		}
		if response.Code != abci.CodeTypeOK {
			continue
		}
		if req.MaxTxBytes >= 0 && total+int64(len(tx)) > req.MaxTxBytes {
			break
		}
		total += int64(len(tx))
		selected = append(selected, tx)
	}
	return &abci.ResponsePrepareProposal{Txs: selected}, nil
}

func (app *bridgeApp) ProcessProposal(ctx context.Context, req *abci.RequestProcessProposal) (*abci.ResponseProcessProposal, error) {
	for _, tx := range req.Txs {
		response, err := app.CheckTx(ctx, &abci.RequestCheckTx{Tx: tx})
		if err != nil {
			return nil, err
		}
		if response.Code != abci.CodeTypeOK {
			return &abci.ResponseProcessProposal{Status: abci.ResponseProcessProposal_REJECT}, nil
		}
	}
	return &abci.ResponseProcessProposal{Status: abci.ResponseProcessProposal_ACCEPT}, nil
}

func (app *bridgeApp) FinalizeBlock(ctx context.Context, req *abci.RequestFinalizeBlock) (*abci.ResponseFinalizeBlock, error) {
	txs, err := rawTransactions(req.Txs)
	if err != nil {
		return nil, err
	}
	if len(req.Hash) != 32 {
		return nil, fmt.Errorf("CometBFT block hash must be 32 bytes, got %d", len(req.Hash))
	}
	var result finalizeResponse
	if err := app.execution.doJSON(
		ctx,
		http.MethodPost,
		"/v2/finalize",
		finalizeEnvelope{
			Height:             req.Height,
			ConsensusBlockHash: hex.EncodeToString(req.Hash),
			Transactions:       txs,
		},
		&result,
	); err != nil {
		return nil, err
	}
	appHash, err := decodeHash(result.NextApplicationHash)
	if err != nil {
		return nil, err
	}
	txResults := make([]*abci.ExecTxResult, len(req.Txs))
	for i := range txResults {
		txResults[i] = &abci.ExecTxResult{Code: abci.CodeTypeOK}
	}
	return &abci.ResponseFinalizeBlock{
		TxResults: txResults,
		AppHash:   appHash,
	}, nil
}

func (app *bridgeApp) Commit(ctx context.Context, _ *abci.RequestCommit) (*abci.ResponseCommit, error) {
	var result commitResponse
	if err := app.execution.doJSON(ctx, http.MethodPost, "/v2/commit", struct{}{}, &result); err != nil {
		return nil, err
	}
	return &abci.ResponseCommit{}, nil
}

func (app *bridgeApp) ListSnapshots(ctx context.Context, _ *abci.RequestListSnapshots) (*abci.ResponseListSnapshots, error) {
	var result snapshotListResponse
	if err := app.execution.doJSON(ctx, http.MethodGet, "/v3/state-sync/snapshots?limit=2", nil, &result); err != nil {
		return nil, err
	}
	snapshots := make([]*abci.Snapshot, 0, len(result.Snapshots))
	for _, item := range result.Snapshots {
		hash, err := decodeHash(item.HashHex)
		if err != nil {
			return nil, err
		}
		metadata, err := base64.StdEncoding.DecodeString(item.MetadataBase64)
		if err != nil {
			return nil, fmt.Errorf("decode snapshot metadata: %w", err)
		}
		snapshots = append(snapshots, &abci.Snapshot{
			Height:   item.Height,
			Format:   item.Format,
			Chunks:   item.Chunks,
			Hash:     hash,
			Metadata: metadata,
		})
	}
	return &abci.ResponseListSnapshots{Snapshots: snapshots}, nil
}

func offerResult(value string) abci.ResponseOfferSnapshot_Result {
	switch strings.ToUpper(value) {
	case "ACCEPT":
		return abci.ResponseOfferSnapshot_ACCEPT
	case "ABORT":
		return abci.ResponseOfferSnapshot_ABORT
	case "REJECT":
		return abci.ResponseOfferSnapshot_REJECT
	case "REJECT_FORMAT":
		return abci.ResponseOfferSnapshot_REJECT_FORMAT
	case "REJECT_SENDER":
		return abci.ResponseOfferSnapshot_REJECT_SENDER
	default:
		return abci.ResponseOfferSnapshot_UNKNOWN
	}
}

func (app *bridgeApp) OfferSnapshot(ctx context.Context, req *abci.RequestOfferSnapshot) (*abci.ResponseOfferSnapshot, error) {
	if req.Snapshot == nil {
		return &abci.ResponseOfferSnapshot{Result: abci.ResponseOfferSnapshot_REJECT}, nil
	}
	var result snapshotOfferResponse
	if err := app.execution.doJSON(
		ctx,
		http.MethodPost,
		"/v3/state-sync/offer",
		snapshotOfferEnvelope{
			Height:         req.Snapshot.Height,
			Format:         req.Snapshot.Format,
			Chunks:         req.Snapshot.Chunks,
			HashHex:        hex.EncodeToString(req.Snapshot.Hash),
			MetadataBase64: base64.StdEncoding.EncodeToString(req.Snapshot.Metadata),
			AppHashHex:     hex.EncodeToString(req.AppHash),
		},
		&result,
	); err != nil {
		return nil, err
	}
	return &abci.ResponseOfferSnapshot{Result: offerResult(result.Result)}, nil
}

func (app *bridgeApp) LoadSnapshotChunk(ctx context.Context, req *abci.RequestLoadSnapshotChunk) (*abci.ResponseLoadSnapshotChunk, error) {
	var result snapshotChunkResponse
	path := fmt.Sprintf(
		"/v3/state-sync/chunk?height=%d&format=%d&chunk=%d",
		req.Height,
		req.Format,
		req.Chunk,
	)
	if err := app.execution.doJSON(ctx, http.MethodGet, path, nil, &result); err != nil {
		return nil, err
	}
	chunk, err := base64.StdEncoding.DecodeString(result.ChunkBase64)
	if err != nil {
		return nil, fmt.Errorf("decode state-sync chunk: %w", err)
	}
	return &abci.ResponseLoadSnapshotChunk{Chunk: chunk}, nil
}

func applyResult(value string) abci.ResponseApplySnapshotChunk_Result {
	switch strings.ToUpper(value) {
	case "ACCEPT":
		return abci.ResponseApplySnapshotChunk_ACCEPT
	case "ABORT":
		return abci.ResponseApplySnapshotChunk_ABORT
	case "RETRY":
		return abci.ResponseApplySnapshotChunk_RETRY
	case "RETRY_SNAPSHOT":
		return abci.ResponseApplySnapshotChunk_RETRY_SNAPSHOT
	case "REJECT_SNAPSHOT":
		return abci.ResponseApplySnapshotChunk_REJECT_SNAPSHOT
	default:
		return abci.ResponseApplySnapshotChunk_UNKNOWN
	}
}

func (app *bridgeApp) ApplySnapshotChunk(ctx context.Context, req *abci.RequestApplySnapshotChunk) (*abci.ResponseApplySnapshotChunk, error) {
	var result snapshotApplyResponse
	if err := app.execution.doJSON(
		ctx,
		http.MethodPost,
		"/v3/state-sync/apply",
		snapshotApplyEnvelope{
			Index:       req.Index,
			ChunkBase64: base64.StdEncoding.EncodeToString(req.Chunk),
			Sender:      req.Sender,
		},
		&result,
	); err != nil {
		return nil, err
	}
	return &abci.ResponseApplySnapshotChunk{
		Result:        applyResult(result.Result),
		RefetchChunks: result.RefetchChunks,
		RejectSenders: result.RejectSenders,
	}, nil
}

func (app *bridgeApp) Query(ctx context.Context, req *abci.RequestQuery) (*abci.ResponseQuery, error) {
	if req.Path != "/app/info" {
		return &abci.ResponseQuery{Code: 1, Log: "supported query path: /app/info"}, nil
	}
	var info infoResponse
	if err := app.execution.doJSON(ctx, http.MethodGet, "/v2/info", nil, &info); err != nil {
		return nil, err
	}
	encoded, err := json.Marshal(info)
	if err != nil {
		return nil, err
	}
	return &abci.ResponseQuery{Code: abci.CodeTypeOK, Value: encoded, Height: info.Height}, nil
}

func main() {
	baseURL := os.Getenv("CRAKBIT_EXECUTION_URL")
	if baseURL == "" {
		baseURL = "http://127.0.0.1:26659"
	}
	token := os.Getenv("CRAKBIT_EXECUTION_TOKEN")
	if len(token) < 24 {
		panic("CRAKBIT_EXECUTION_TOKEN must be at least 24 characters")
	}
	listen := os.Getenv("CRAKBIT_ABCI_LISTEN")
	if listen == "" {
		listen = "tcp://127.0.0.1:26658"
	}

	app := newBridge(baseURL, token)
	srv, err := abciserver.NewServer(listen, "socket", app)
	if err != nil {
		panic(err)
	}
	if err := srv.Start(); err != nil {
		panic(err)
	}
	fmt.Printf("Crakbit CometBFT bridge %s listening on %s -> %s\n", bridgeVersion, listen, baseURL)

	signals := make(chan os.Signal, 1)
	signal.Notify(signals, syscall.SIGINT, syscall.SIGTERM)
	<-signals
	if err := srv.Stop(); err != nil {
		fmt.Fprintf(os.Stderr, "bridge shutdown error: %v\n", err)
	}
}
