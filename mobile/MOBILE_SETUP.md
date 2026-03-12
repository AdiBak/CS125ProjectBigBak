# Big Bak – React Native (Expo) mobile app

This folder contains the **frontend mobile app** for Big Bak. It’s built with **React Native** and **Expo SDK 54**, so it works with the **Expo Go** app from the App Store on your iPhone.

---

## Expo Go compatibility

This project uses **Expo SDK 54** so it runs in the **Expo Go** version available on the iOS App Store. If you previously saw “project is incompatible with this version of Expo Go”, that was because the project was on SDK 55. It’s now upgraded to SDK 54.

1. **Update Expo Go** on your iPhone (App Store → Expo Go → Update).
2. If it still says incompatible, uninstall Expo Go and install it again from the App Store to get the latest build.

---

## Prerequisites

1. **Node.js** (v18+) – [nodejs.org](https://nodejs.org)
2. **iPhone (physical device)**  
   - Install **Expo Go** from the App Store: [Expo Go](https://apps.apple.com/app/expo-go/id982107779)  
   - Your phone and your Mac must be on the **same Wi‑Fi network**
3. **Backend running** – The app talks to your FastAPI backend. Start it from the repo root:
   ```bash
   cd backend && python main.py
   # or: uvicorn main:app --host 0.0.0.0 --port 8000
   ```

---

## 1. Install dependencies

From the repo root:

```bash
cd mobile
npm install
```

---

## 2. Run the app and open on your iPhone

Start the Expo dev server:

```bash
npm start
# or: npx expo start
```

Then:

- **Option A – Expo Go (easiest)**  
  - On your iPhone, open the **Camera** app and scan the **QR code** shown in the terminal (or in the browser page that opened).  
  - Or open the **Expo Go** app and scan the same QR code.  
  - The app will load on your phone.

- **Option B – iOS Simulator**  
  - In the terminal where `npm start` is running, press **`i`** to open the iOS Simulator (requires Xcode to be installed).

---

## 3. Point the app at your backend (using ngrok – recommended)

On a **physical iPhone**, Expo Go cannot call `http://localhost:8000` directly. We tunnel your local backend over **HTTPS** using **ngrok**, and the app talks to that URL.

Everyone on the team can follow these same steps on their own machine:

1. **Start the backend** (from repo root, in one terminal):
   ```bash
   cd backend
   python main.py
   # serves http://0.0.0.0:8000
   ```

2. **Install and configure ngrok** (one-time):
   - Go to [ngrok.com](https://ngrok.com), create a free account, and install ngrok.
   - Authenticate once:
     ```bash
     ngrok config add-authtoken YOUR_TOKEN
     ```

3. **Start an HTTPS tunnel to your backend** (second terminal):
   ```bash
   ngrok http 8000
   ```
   You’ll see something like:
   ```text
   Forwarding  https://your-subdomain.ngrok-free.dev -> http://localhost:8000
   ```

4. **Tell the mobile app which backend to use**:
   - In the `mobile` folder, create or edit `.env`:
     ```bash
     cd mobile
     echo "EXPO_PUBLIC_API_URL=https://your-subdomain.ngrok-free.dev" > .env
     ```
     Replace the URL with the **https** URL from the ngrok output.

5. **Restart Expo and reload the app**:
   - Stop the Expo dev server (`Ctrl+C` in the `mobile` terminal), then run `npm start` again.
   - Reload the app in Expo Go on your iPhone (pull to refresh or shake → Reload).

> **Simulator / web shortcut:** If you are testing only in the **iOS Simulator** or **web**, you can skip ngrok and instead set:
> ```env
> EXPO_PUBLIC_API_URL=http://localhost:8000
> ```
> while the backend is running locally.

---

## 3b. Troubleshooting: "Network request failed" (Mac works, iPhone doesn’t)

If **Safari/curl on your Mac** can open `http://YOUR_MAC_IP:8000/api/v1/health` but the **app on your iPhone** shows "Network request failed", the iPhone is probably being blocked from reaching your Mac.

1. **Test from the iPhone**
   - On your **iPhone**, open **Safari** and go to: `http://172.31.151.76:8000/api/v1/health` (use your Mac’s IP).
   - If you see `{"status":"healthy",...}` → the network is fine; the issue may be Expo Go or app config (reload the app, restart Expo).
   - If Safari on the iPhone **cannot** load that URL → your **Mac firewall** is likely blocking incoming connections from the iPhone.

2. **Allow incoming connections on your Mac**
   - **System Settings → Network → Firewall** (or **Security & Privacy → Firewall**).
   - If the firewall is **On**:
     - Click **Options** (or **Firewall Options**).
     - Ensure **Python** (or **Terminal**) is set to **Allow incoming connections**, **or**
     - Add a rule to allow **TCP port 8000** for incoming connections.
   - Alternatively, temporarily turn the firewall **Off** to confirm the app then works; if it does, add a proper rule for port 8000 and turn the firewall back on.

3. **Same Wi‑Fi**
   - iPhone and Mac must be on the **same Wi‑Fi network** (not cellular, not a guest network). Verify in iPhone **Settings → Wi‑Fi** and on the Mac in **System Settings → Network → Wi‑Fi**.

---

## 3c. If you still see "Network request failed"

If Safari on your iPhone can open your health check URL but the app still shows  
**"Network request failed"**, check the following:

1. **`EXPO_PUBLIC_API_URL` is HTTPS, not HTTP**  
   - In `mobile/.env`, the value must start with `https://` and point to your **ngrok** URL  
     (for example: `https://your-subdomain.ngrok-free.dev`), not `http://localhost:8000`.

2. **Expo dev server was restarted after changes**  
   - After editing `.env`, stop Expo (`Ctrl+C`), run `npm start` again, then reload the app in Expo Go.

3. **ngrok + backend are running**  
   - `python main.py` is running in `backend/`.  
   - `ngrok http 8000` is running and still shows a forwarding HTTPS URL.

---

## 4. Project structure

- **`app/(tabs)/`** – Tab screens:
  - **Home** – Context and recommendation cards (from `/api/v1/users/{id}/home`).
  - **Inventory** – User inventory list and search (from `/api/v1/users/{id}/inventory`).
  - **Settings** – User profile and preferences (from `/api/v1/users/{id}/settings`).
- **`lib/api.ts`** – API client and types; **edit `API_BASE_URL`** here (or via `EXPO_PUBLIC_API_URL`) for your backend.
- **`constants/Colors.ts`** – Theme colors (aligned with the Big Bak mockup).

---

## 5. Useful commands

| Command            | Description                          |
|--------------------|--------------------------------------|
| `npm start`        | Start Expo dev server                |
| `npm run ios`      | Start and open iOS Simulator         |
| `npm run web`      | Run in the web browser (for quick UI check) |

---

## 6. Next steps (from your progress report)

- **Wire actions**: “Add to Inventory” and “Dismiss” on Home; “Restock” on Inventory (backend already has `POST .../inventory/restock`).
- **Product detail screen**: Add a stack screen or modal for product detail (urgency score, nearby stores, similar products) and navigate from a recommendation card.
- **Categories**: Use real categories from the backend in the Inventory tabs.
- **Location**: Pass device location (`expo-location`) into the home dashboard API for “Near Trader Joe’s” context.

Once the backend is running and `API_BASE_URL` is set to your Mac’s IP, you can open the app in **Expo Go** on your iPhone and see live data from your API.
