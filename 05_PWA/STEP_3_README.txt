STEP 3 — RUN THE FIRST PWA

1. Install Node.js LTS if it is not already installed.
2. Open a terminal in this project folder.
3. Run:
       npm install
4. Then:
       npm run dev
5. Open the local URL printed by Vite.

The current prototype already includes the paper's normalized pwa_data.json.

Next step after visual review:
- polish UI
- lock the analytical snapshot
- add the missing Risk Environment monthly series after its source is confirmed
- separate frontend from remote data so data can update without redeploying
- add offline/demo fallback
