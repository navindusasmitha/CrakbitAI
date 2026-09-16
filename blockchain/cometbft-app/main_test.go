package main

import (
	"context"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	abci "github.com/cometbft/cometbft/abci/types"
)

func mockExecutionServer(t *testing.T) *httptest.Server {
	t.Helper()
	zeroHash := hex.EncodeToString(make([]byte, 32))
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("Authorization") != "Bearer test-token-12345678901234567890" {
			http.Error(w, `{"detail":"unauthorized"}`, http.StatusUnauthorized)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		switch r.URL.Path {
		case "/v2/info":
			_ = json.NewEncoder(w).Encode(map[string]any{
				"protocol":         "crakbit-execution/2",
				"chain_id":         "crakbit-test",
				"height":           0,
				"application_hash": zeroHash,
			})
		case "/v2/check-tx":
			_ = json.NewEncoder(w).Encode(map[string]any{
				"accepted": true,
				"txid":     "abc",
			})
		case "/v2/finalize":
			_ = json.NewEncoder(w).Encode(map[string]any{
				"protocol":              "crakbit-execution/2",
				"height":                1,
				"next_application_hash": zeroHash,
				"request_hash":          zeroHash,
				"transaction_count":     1,
			})
		case "/v2/commit":
			_ = json.NewEncoder(w).Encode(map[string]any{
				"protocol":         "crakbit-execution/2",
				"height":           1,
				"application_hash": zeroHash,
				"committed":        true,
			})
		case "/v3/state-sync/snapshots":
			_ = json.NewEncoder(w).Encode(map[string]any{
				"snapshots": []map[string]any{
					{
						"height":          12,
						"format":          1,
						"chunks":          1,
						"hash_hex":        zeroHash,
						"metadata_base64": base64.StdEncoding.EncodeToString([]byte(`{"app":"crakbit"}`)),
					},
				},
			})
		case "/v3/state-sync/chunk":
			_ = json.NewEncoder(w).Encode(map[string]any{
				"chunk_base64": base64.StdEncoding.EncodeToString([]byte("snapshot-data")),
			})
		case "/v3/state-sync/offer":
			_ = json.NewEncoder(w).Encode(map[string]any{"result": "ACCEPT"})
		case "/v3/state-sync/apply":
			_ = json.NewEncoder(w).Encode(map[string]any{
				"result":          "ACCEPT",
				"refetch_chunks": []uint32{},
				"reject_senders": []string{},
			})
		default:
			http.NotFound(w, r)
		}
	}))
}

func TestInfoCheckFinalizeAndCommit(t *testing.T) {
	server := mockExecutionServer(t)
	defer server.Close()
	app := newBridge(server.URL, "test-token-12345678901234567890")
	ctx := context.Background()

	info, err := app.Info(ctx, &abci.RequestInfo{})
	if err != nil {
		t.Fatal(err)
	}
	if info.LastBlockHeight != 0 || len(info.LastBlockAppHash) != 32 {
		t.Fatalf("unexpected info response: %#v", info)
	}

	tx := []byte(`{"chain_id":"crakbit-test"}`)
	// Raw string above contains backslashes, so use a real JSON transaction below.
	tx = []byte(`{"noop":true}`)
	// Replace the escaped fixture with valid JSON bytes for bridge framing tests.
	tx = []byte("{\"chain_id\":\"crakbit-test\"}")
	check, err := app.CheckTx(ctx, &abci.RequestCheckTx{Tx: tx})
	if err != nil {
		t.Fatal(err)
	}
	if check.Code != abci.CodeTypeOK {
		t.Fatalf("unexpected CheckTx code: %d", check.Code)
	}

	blockHash := make([]byte, 32)
	blockHash[0] = 0x42
	finalized, err := app.FinalizeBlock(ctx, &abci.RequestFinalizeBlock{
		Height: 1,
		Hash:   blockHash,
		Txs:    [][]byte{tx},
	})
	if err != nil {
		t.Fatal(err)
	}
	if len(finalized.AppHash) != 32 || len(finalized.TxResults) != 1 {
		t.Fatalf("unexpected finalize response: %#v", finalized)
	}

	if _, err := app.Commit(ctx, &abci.RequestCommit{}); err != nil {
		t.Fatal(err)
	}
}

func TestSnapshotLifecycleBridge(t *testing.T) {
	server := mockExecutionServer(t)
	defer server.Close()
	app := newBridge(server.URL, "test-token-12345678901234567890")
	ctx := context.Background()

	listed, err := app.ListSnapshots(ctx, &abci.RequestListSnapshots{})
	if err != nil {
		t.Fatal(err)
	}
	if len(listed.Snapshots) != 1 {
		t.Fatalf("expected one snapshot, got %d", len(listed.Snapshots))
	}
	snapshot := listed.Snapshots[0]
	if snapshot.Height != 12 || snapshot.Format != 1 || snapshot.Chunks != 1 || len(snapshot.Hash) != 32 {
		t.Fatalf("unexpected snapshot descriptor: %#v", snapshot)
	}

	offered, err := app.OfferSnapshot(ctx, &abci.RequestOfferSnapshot{
		Snapshot: snapshot,
		AppHash:  make([]byte, 32),
	})
	if err != nil {
		t.Fatal(err)
	}
	if offered.Result != abci.ResponseOfferSnapshot_ACCEPT {
		t.Fatalf("snapshot was not accepted: %#v", offered)
	}

	loaded, err := app.LoadSnapshotChunk(ctx, &abci.RequestLoadSnapshotChunk{
		Height: snapshot.Height,
		Format: snapshot.Format,
		Chunk:  0,
	})
	if err != nil {
		t.Fatal(err)
	}
	if string(loaded.Chunk) != "snapshot-data" {
		t.Fatalf("unexpected snapshot chunk: %q", loaded.Chunk)
	}

	applied, err := app.ApplySnapshotChunk(ctx, &abci.RequestApplySnapshotChunk{
		Index:  0,
		Chunk:  loaded.Chunk,
		Sender: "peer-id",
	})
	if err != nil {
		t.Fatal(err)
	}
	if applied.Result != abci.ResponseApplySnapshotChunk_ACCEPT {
		t.Fatalf("snapshot chunk was not accepted: %#v", applied)
	}
}
