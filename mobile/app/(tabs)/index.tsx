import { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
  Pressable,
} from 'react-native';

import Colors from '@/constants/Colors';
import { useColorScheme } from '@/components/useColorScheme';
import * as Location from 'expo-location';
import {
  getHomeDashboard,
  getUrgencyLabel,
  API_BASE_URL,
  restockItem,
  type RecommendationItem,
  type RecommendationResponse,
} from '@/lib/api';
import * as Linking from 'expo-linking';
import { useRouter } from 'expo-router';

export default function HomeScreen() {
  const colorScheme = useColorScheme();
  const c = Colors[colorScheme ?? 'light'];
  const router = useRouter();
  const [data, setData] = useState<RecommendationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(new Set());
  const [addingId, setAddingId] = useState<string | null>(null);

  const load = async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    setError(null);
    try {
      let lat: number | undefined;
      let lon: number | undefined;

      try {
        const { status } = await Location.requestForegroundPermissionsAsync();
        if (status === 'granted') {
          const pos = await Location.getCurrentPositionAsync({});
          lat = pos.coords.latitude;
          lon = pos.coords.longitude;
        }
      } catch {
        // If location fails, we just fall back to non-contextual home dashboard.
      }

      const res = await getHomeDashboard(lat, lon);
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleAddToInventory = async (itemKey: string) => {
    setAddingId(itemKey);
    try {
      await restockItem(itemKey);
      await load(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to add');
    } finally {
      setAddingId(null);
    }
  };

  const handleDismiss = (itemKey: string) => {
    setDismissedIds((prev) => new Set(prev).add(itemKey));
  };

  useEffect(() => {
    load();
  }, []);

  if (loading && !data) {
    return (
      <View style={[styles.centered, { backgroundColor: c.background }]}>
        <ActivityIndicator size="large" color={c.tint} />
        <Text style={[styles.errorText, { color: c.text }]}>Loading recommendations…</Text>
      </View>
    );
  }

  return (
    <ScrollView
      style={[styles.container, { backgroundColor: c.background }]}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={() => load(true)} colors={[c.tint]} />
      }>
      {/* Header */}
      <View style={[styles.header, { backgroundColor: c.tint }]}>
        <Text style={styles.headerTitle}>Big Bak</Text>
        <View style={styles.notificationBadge}>
          <Text style={styles.notificationEmoji}>🔔</Text>
        </View>
      </View>

      {error ? (
        <View style={[styles.errorBox, { borderColor: c.border }]}>
          <Text style={[styles.errorText, { color: c.text }]}>{error}</Text>
          <Text style={[styles.hint, { color: c.text }]}>
            Expo Go on iOS blocks HTTP. Use HTTPS: run "ngrok http 8000" on your Mac, then set
            EXPO_PUBLIC_API_URL to the https URL in mobile/.env and restart Expo. See MOBILE_SETUP.md.
          </Text>
          <TouchableOpacity
            style={[styles.linkButton, { backgroundColor: c.tint }]}
            onPress={() => Linking.openURL(`${API_BASE_URL}/api/v1/health`)}>
            <Text style={styles.linkButtonText}>Open API URL in Safari</Text>
          </TouchableOpacity>
        </View>
      ) : null}

      {data?.context ? (
        <View style={[styles.contextCard, { backgroundColor: '#e67e22' }]}>
          <Text style={styles.contextIcon}>📍</Text>
          <Text style={styles.contextText}>{data.context}</Text>
        </View>
      ) : null}

      {data?.recommendations?.length
        ? data.recommendations
            .filter((rec) => !dismissedIds.has(rec.item))
            .map((rec, i) => (
              <RecommendationCard
                key={rec.item}
                item={rec}
                colors={c}
                onAddToInventory={handleAddToInventory}
                onDismiss={handleDismiss}
                onPressCard={() =>
                  router.push({
                    pathname: '/product',
                    params: {
                      item: rec.item,
                      urgency: String(rec.urgency),
                      reason: rec.reason,
                      products: JSON.stringify(rec.suggested_products ?? []),
                      nearest_store_name: rec.nearest_store_name ?? '',
                      nearest_store_address: rec.nearest_store_address ?? '',
                      nearest_store_distance_mi: rec.nearest_store_distance_mi != null ? String(rec.nearest_store_distance_mi) : '',
                    },
                  })
                }
                isAdding={addingId === rec.item}
              />
            ))
        : !error && (
            <View style={styles.empty}>
              <Text style={[styles.emptyText, { color: c.text }]}>
                No recommendations right now. Add items to your inventory to get suggestions.
              </Text>
            </View>
          )}

      <View style={{ height: 24 }} />
    </ScrollView>
  );
}

function RecommendationCard({
  item,
  colors,
  onAddToInventory,
  onDismiss,
  onPressCard,
  isAdding,
}: {
  item: RecommendationItem;
  colors: typeof Colors.light;
  onAddToInventory: (itemKey: string) => void;
  onDismiss: (itemKey: string) => void;
  onPressCard?: () => void;
  isAdding: boolean;
}) {
  const urgency = getUrgencyLabel(item.urgency);
  const bannerStyle =
    urgency === 'High'
      ? { backgroundColor: '#fee', color: colors.urgencyHigh }
      : urgency === 'Medium'
        ? { backgroundColor: '#fef9e7', color: colors.urgencyMedium }
        : { backgroundColor: '#e8f8f5', color: colors.urgencyLow };

  const product = item.suggested_products?.[0];
  const name = product?.name ?? item.item;
  const price = product?.price ?? '—';
  const match = product?.relevance;
  const rawStoreLabel = item.nearest_store_name ?? "Trader Joe's";
  const storeLabel = rawStoreLabel.replace(/\s*\(Mock\)/i, '');
  const distMi = item.nearest_store_distance_mi;
  const storeSubtext = distMi != null ? `${distMi} mi` : 'nearby';

  return (
    <Pressable
      onPress={onPressCard}
      style={({ pressed }) => [
        styles.card,
        { backgroundColor: colors.cardBg, borderColor: colors.border },
        pressed && { opacity: 0.9 },
      ]}>
      <View style={[styles.urgencyBanner, bannerStyle]}>
        <Text style={styles.urgencyText}>{urgency} Priority</Text>
      </View>
      <View style={styles.cardContent}>
        <View style={styles.productRow}>
          <View style={[styles.productImage, { backgroundColor: colors.background }]}>
            <Text style={styles.productEmoji}>🛒</Text>
          </View>
          <View style={styles.productInfo}>
            <Text style={[styles.productName, { color: colors.text }]}>{name}</Text>
            <Text style={[styles.productPrice, { color: colors.price }]}>{price}</Text>
          </View>
        </View>
        <View style={[styles.reasonBox, { borderLeftColor: colors.reasonBorder }]}>
          <Text style={styles.reasonLabel}>Why Now?</Text>
          <Text style={[styles.reasonText, { color: colors.text }]}>{item.reason}</Text>
        </View>
        <Text style={[styles.storeInfo, { color: colors.text }]}>
          📍 {storeLabel} — {storeSubtext}
        </Text>
        <View style={styles.actions}>
          <TouchableOpacity
            style={[styles.btn, styles.btnPrimary, { backgroundColor: colors.tint }]}
            onPress={() => onAddToInventory(item.item)}
            disabled={isAdding}>
            <Text style={styles.btnPrimaryText}>
              {isAdding ? 'Adding…' : 'Add to Inventory'}
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.btn, styles.btnSecondary, { backgroundColor: colors.background }]}
            onPress={() => onDismiss(item.item)}>
            <Text style={[styles.btnSecondaryText, { color: colors.text }]}>Dismiss</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { paddingBottom: 24 },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center', gap: 12 },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 16,
    paddingTop: 48,
  },
  headerTitle: { fontSize: 24, fontWeight: '600', color: '#fff' },
  notificationBadge: { width: 36, height: 36, borderRadius: 18, backgroundColor: 'rgba(255,255,255,0.2)', justifyContent: 'center', alignItems: 'center' },
  notificationEmoji: { fontSize: 18 },
  errorBox: { margin: 20, padding: 16, borderRadius: 12, backgroundColor: '#fff3cd' },
  errorText: { fontSize: 14 },
  hint: { fontSize: 12, marginTop: 8, opacity: 0.9 },
  linkButton: { marginTop: 12, padding: 12, borderRadius: 8, alignItems: 'center' },
  linkButtonText: { color: '#fff', fontWeight: '600', fontSize: 14 },
  contextCard: {
    flexDirection: 'row',
    alignItems: 'center',
    marginHorizontal: 20,
    marginTop: 16,
    padding: 16,
    borderRadius: 12,
    gap: 8,
  },
  contextIcon: { fontSize: 20 },
  contextText: { fontSize: 14, color: '#fff', flex: 1 },
  empty: { margin: 20 },
  emptyText: { fontSize: 15 },
  card: {
    marginHorizontal: 20,
    marginTop: 16,
    borderRadius: 12,
    borderWidth: 1,
    overflow: 'hidden',
  },
  urgencyBanner: { paddingVertical: 8, paddingHorizontal: 16 },
  urgencyText: { fontSize: 12, fontWeight: '600', textTransform: 'uppercase' },
  cardContent: { padding: 16 },
  productRow: { flexDirection: 'row', gap: 16, marginBottom: 12 },
  productImage: { width: 80, height: 80, borderRadius: 8, justifyContent: 'center', alignItems: 'center' },
  productEmoji: { fontSize: 40 },
  productInfo: { flex: 1, justifyContent: 'center' },
  productName: { fontSize: 16, fontWeight: '600', marginBottom: 4 },
  productPrice: { fontSize: 18, fontWeight: '700' },
  matchScore: { fontSize: 11, marginTop: 2, opacity: 0.7 },
  reasonBox: {
    backgroundColor: '#f8f9fa',
    padding: 12,
    borderRadius: 8,
    borderLeftWidth: 4,
    marginBottom: 12,
  },
  reasonLabel: { fontSize: 11, color: '#7f8c8d', textTransform: 'uppercase', marginBottom: 4, fontWeight: '600' },
  reasonText: { fontSize: 13 },
  storeInfo: { fontSize: 13, marginBottom: 12 },
  actions: { flexDirection: 'row', gap: 8 },
  btn: { flex: 1, padding: 12, borderRadius: 8, alignItems: 'center' },
  btnPrimary: {},
  btnPrimaryText: { color: '#fff', fontWeight: '600', fontSize: 14 },
  btnSecondary: {},
  btnSecondaryText: { fontSize: 14, fontWeight: '600' },
});
