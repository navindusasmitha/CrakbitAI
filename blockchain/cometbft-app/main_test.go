package main

import (
	"context"
	"encoding/hex"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	abci "github.com/cometbft/cometbft/abci/types"
)

func mockExecutionServer(t *testing.T) *httptest.Server {
	t.Helper()
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
				"application_hash": string(make([]byte, 0)),
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
				"next_application_hash": hex.EncodeToString(make([]byte, 32)),
				"request_hash":          hex.EncodeToString(make([]byte, 32)),
				"transaction_count":     1,
			})
		case "/v2/commit":
			_ = json.NewEncoder(w).Encode(map[string]any{
				"protocol":         "crakbit-execution/2",
				"height":           1,
				"application_hash": hex.EncodeToString(make([]byte, 32)),
				"committed":        true,
			})
		default:
			http.NotFound(w, r)
		}
	}))
}

func TestCheckFinalizeAndCommit(t *testing.T) {
	server := mockExecutionServer(t)
	defer server.Close()
	app := newBridge(server.URL, "test-token-12345678901234567890")
	ctx := context.Background()

	tx := []byte(`{"chain_id":"crakbit-test"}`)
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
