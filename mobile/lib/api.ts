/**
 * Big Bak API client.
 * Point BASE_URL to your backend (use your Mac's LAN IP when testing on physical iPhone).
 */

// Use your computer's IP when running on a real device (e.g. http://192.168.1.5:8000).
// Must include http:// and port (e.g. :8000). For simulator you can use http://localhost:8000.
const raw = process.env.EXPO_PUBLIC_API_URL || '172.31.151.76';
const withScheme = raw.startsWith('http') ? raw : `http://${raw}`;
export const API_BASE_URL = withScheme.includes(':') ? withScheme : `${withScheme}:8000`;

const USER_ID = 'test_user';

export type ProductSuggestion = {
  name: string;
  price: string;
  relevance: string;
};

export type RecommendationItem = {
  item: string;
  urgency: number;
  reason: string;
  suggested_products: ProductSuggestion[];
  nearest_store_name?: string | null;
  nearest_store_address?: string | null;
  nearest_store_distance_mi?: number | null;
};

export type RecommendationResponse = {
  user_id: string;
  context: string;
  recommendations: RecommendationItem[];
  low_stock_items?: string[];
};

export type InventoryItem = {
  item_name: string;
  stock_percentage: number;
  last_bought_days_ago: number;
  category: string;
};

export type UserSettings = {
  user_name: string;
  email: string;
  preferred_brands: string[];
  price_sensitivity: string;
  location_alerts: boolean;
  low_stock_warnings: boolean;
  push_token?: string | null;
};

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  try {
    const res = await fetch(url, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...options?.headers },
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`API ${res.status}: ${text}`);
    }
    return res.json();
  } catch (e) {
    const message = e instanceof Error ? e.message : 'Unknown error';
    if (message === 'Network request failed' || message.includes('Network request failed')) {
      throw new Error(
        `Network request failed. URL: ${url}\n\n` +
          '• Open this URL in Safari ON YOUR IPHONE to test. If it fails there too, the Mac firewall is likely blocking the iPhone. See MOBILE_SETUP.md.'
      );
    }
    throw e;
  }
}

export async function getHomeDashboard(lat?: number, lon?: number) {
  let path = `/api/v1/users/${USER_ID}/home`;
  if (lat != null && lon != null) {
    path += `?lat=${lat}&lon=${lon}`;
  }
  return fetchApi<RecommendationResponse>(path);
}

export async function getInventory() {
  return fetchApi<InventoryItem[]>(`/api/v1/users/${USER_ID}/inventory`);
}

export async function getUserSettings() {
  return fetchApi<UserSettings>(`/api/v1/users/${USER_ID}/settings`);
}

export type UserSettingsUpdate = Partial<UserSettings>;

export async function updateUserSettings(update: UserSettingsUpdate) {
  return fetchApi<UserSettings>(`/api/v1/users/${USER_ID}/settings`, {
    method: 'PATCH',
    body: JSON.stringify(update),
  });
}

export async function restockItem(itemName: string) {
  return fetchApi<{ status: string }>(
    `/api/v1/users/${USER_ID}/inventory/restock?item_name=${encodeURIComponent(itemName)}`,
    { method: 'POST' }
  );
}

/** Set an item's stock (0–1) and days since last buy. Creates the item if missing. */
export async function setInventoryItem(
  itemName: string,
  stock: number,
  lastBuyDaysAgo: number
) {
  return fetchApi<{ status: string }>(
    `/api/v1/users/${USER_ID}/inventory`,
    {
      method: 'PATCH',
      body: JSON.stringify({
        item_name: itemName,
        stock,
        last_buy: lastBuyDaysAgo,
      }),
    }
  );
}

export function getUrgencyLabel(urgency: number): 'High' | 'Medium' | 'Low' {
  if (urgency >= 0.6) return 'High';
  if (urgency >= 0.4) return 'Medium';
  return 'Low';
}
