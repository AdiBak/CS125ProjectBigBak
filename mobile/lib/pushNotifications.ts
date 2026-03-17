import * as Device from 'expo-device';
import * as Notifications from 'expo-notifications';

/**
 * Request notification permission (for local notifications).
 * No push token or EAS project ID needed.
 */
export async function requestNotificationPermission(): Promise<boolean> {
  if (!Device.isDevice) return false;
  try {
    const { status: existing } = await Notifications.getPermissionsAsync();
    if (existing === 'granted') return true;
    const { status } = await Notifications.requestPermissionsAsync();
    return status === 'granted';
  } catch {
    return false;
  }
}

const LOW_STOCK_THROTTLE_MS = 4 * 60 * 60 * 1000; // 4 hours
let lastLowStockNotifAt = 0;

/**
 * Schedule a local notification for low-stock items (throttled to once per 4 hours).
 * Call when Home loads and the API returns low_stock_items.
 */
export async function scheduleLowStockNotification(items: string[]): Promise<void> {
  if (!items?.length) return;
  const now = Date.now();
  if (now - lastLowStockNotifAt < LOW_STOCK_THROTTLE_MS) return;
  const granted = await requestNotificationPermission();
  if (!granted) return;
  try {
    const body =
      items.length === 1
        ? `'${items[0]}' is running low.`
        : `Your ${items.slice(0, 5).join(', ')}${items.length > 5 ? '…' : ''} are running low.`;
    await Notifications.scheduleNotificationAsync({
      content: {
        title: 'Low stock',
        body,
        sound: true,
      },
      trigger: {
        type: Notifications.SchedulableTriggerInputTypes.TIME_INTERVAL,
        seconds: 2,
      },
    });
    lastLowStockNotifAt = now;
  } catch (e) {
    console.warn('Local notification schedule failed:', e);
  }
}
