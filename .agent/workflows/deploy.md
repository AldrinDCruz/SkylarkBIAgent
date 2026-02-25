---
description: Deploy Skylark BI Agent to Production
---

This workflow guides you through deploying the Backend to Railway and the Frontend to Vercel.

1. **GitHub Setup**
   - Push your code to a GitHub repository:
     ```powershell
     git add .
     git commit -m "Deployment preparation"
     git push origin main
     ```

2. **Backend (Railway)**
   - Sign in to [Railway.app](https://railway.app).
   - Click **New Project** -> **Deploy from GitHub**.
   - Select the `skylark` repo.
   - Set **Root Directory** to `backend`.
   - Add environment variables: `GOOGLE_API_KEY`, `MONDAY_API_TOKEN`, `DEALS_BOARD_ID`, `WO_BOARD_ID`.
   - Copy the generated endpoint URL.

3. **Frontend (Vercel)**
   - Sign in to [Vercel.com](https://vercel.com).
   - Import the `skylark` repo.
   - Set **Root Directory** to `frontend`.
   - Add Environment Variable: `VITE_API_URL` (set to your Railway URL).
   - Click **Build and Deploy**.
