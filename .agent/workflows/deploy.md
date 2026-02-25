---
description: Deploy Skylark BI Agent to Production (Render & Vercel)
---

This workflow guides you through deploying the Backend to Render and the Frontend to Vercel.

1. **GitHub Setup**
   - Ensure all changes are pushed:
     ```powershell
     git add .
     git commit -m "Render/Vercel deployment prep"
     git push origin main
     ```

2. **Backend (Render)**
   - Sign in to [Render.com](https://render.com).
   - Click **New +** -> **Web Service**.
   - Connect your `skylark` repo.
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Add Env Vars: `GOOGLE_API_KEY`, `MONDAY_API_TOKEN`, `DEALS_BOARD_ID`, `WO_BOARD_ID`.
   - Copy the unique `.onrender.com` URL.

3. **Frontend (Vercel)**
   - Sign in to [Vercel.com](https://vercel.com).
   - Import the `skylark` repo.
   - Set **Root Directory** to `frontend`.
   - Add Env Var: `VITE_API_URL` (set to your Render URL).
   - Click **Deploy**.
