import React, { useCallback, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  RefreshControl,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  View,
  Text,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { useRouter } from 'expo-router';

import Colors from '@/constants/Colors';
import { useColorScheme } from '@/components/useColorScheme';
import { getInventory, restockItem, type InventoryItem as ApiInventoryItem } from '@/lib/api';

export default function InventoryScreen() {
  const colorScheme = useColorScheme();
  const c = Colors[colorScheme ?? 'light'];
  const router = useRouter();
  const [items, setItems] = useState<ApiInventoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [search, setSearch] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [restockingId, setRestockingId] = useState<string | null>(null);

  const load = async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    setError(null);
    try {
      const data = await getInventory();
      setItems(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load inventory');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // Poll inventory while this tab is focused so server-side decay updates without pull-to-refresh.
  useFocusEffect(
    useCallback(() => {
      let alive = true;
      void load(true);
      const id = setInterval(async () => {
        try {
          const data = await getInventory();
          if (alive) setItems(data);
        } catch {
          // ignore transient errors during background poll
        }
      }, 1000);
      return () => {
        alive = false;
        clearInterval(id);
      };
    }, [])
  );

  const handleRestock = async (itemName: string) => {
    setRestockingId(itemName);
    setError(null);
    try {
      await restockItem(itemName);
      await load(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to restock');
    } finally {
      setRestockingId(null);
    }
  };

  const filtered = search.trim()
    ? items.filter((i) => i.item_name.toLowerCase().includes(search.toLowerCase()))
    : items;

  const stockColor = (pct: number) =>
    pct >= 60 ? c.urgencyLow : pct >= 30 ? c.urgencyMedium : c.urgencyHigh;

  if (loading && items.length === 0) {
    return (
      <View style={[styles.centered, { backgroundColor: c.background }]}>
        <ActivityIndicator size="large" color={c.tint} />
        <Text style={[styles.errorText, { color: c.text }]}>Loading inventory…</Text>
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: c.background }]}>
      <View style={[styles.header, { backgroundColor: c.tint }]}>
        <Text style={styles.headerTitle}>My Inventory</Text>
        <TouchableOpacity onPress={() => router.push('/add-item')} hitSlop={12}>
          <Text style={styles.plusIcon}>➕</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.searchWrap}>
        <Text style={styles.searchIcon}>🔍</Text>
        <TextInput
          style={[styles.searchInput, { backgroundColor: c.cardBg, color: c.text, borderColor: c.border }]}
          placeholder="Search items..."
          placeholderTextColor="#95a5a6"
          value={search}
          onChangeText={setSearch}
        />
      </View>

      <View style={styles.tabs}>
        <View style={[styles.tab, { backgroundColor: c.tint }]}>
          <Text style={styles.tabTextActive}>All</Text>
        </View>
        <View style={[styles.tab, { backgroundColor: c.cardBg, borderColor: c.border }]}>
          <Text style={[styles.tabText, { color: c.text }]}>Food</Text>
        </View>
        <View style={[styles.tab, { backgroundColor: c.cardBg, borderColor: c.border }]}>
          <Text style={[styles.tabText, { color: c.text }]}>Snacks</Text>
        </View>
      </View>

      {error ? (
        <View style={styles.errorBox}>
          <Text style={[styles.errorText, { color: c.text }]}>{error}</Text>
        </View>
      ) : null}

      <FlatList
        data={filtered}
        keyExtractor={(item) => item.item_name}
        contentContainerStyle={styles.listContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={() => load(true)} colors={[c.tint]} />
        }
        renderItem={({ item }) => (
          <TouchableOpacity
            style={[styles.inventoryItem, { backgroundColor: c.cardBg, borderColor: c.border }]}
            onPress={() =>
              router.push({
                pathname: '/edit-inventory-item',
                params: {
                  item_name: item.item_name,
                  stock_percentage: String(item.stock_percentage),
                  last_bought_days_ago: String(item.last_bought_days_ago),
                },
              })
            }
            activeOpacity={0.7}>
            <View style={[styles.itemIcon, { backgroundColor: c.background }]}>
              <Text style={styles.itemEmoji}>📦</Text>
            </View>
            <View style={styles.itemDetails}>
              <Text style={[styles.itemName, { color: c.text }]}>{item.item_name}</Text>
              <View style={[styles.stockBarBg, { backgroundColor: c.background }]}>
                <View
                  style={[
                    styles.stockBar,
                    { width: `${Math.min(100, item.stock_percentage)}%`, backgroundColor: stockColor(item.stock_percentage) },
                  ]}
                />
              </View>
              <Text style={[styles.lastBuy, { color: c.text }]}>
                Last bought {item.last_bought_days_ago} days ago
              </Text>
            </View>
            <TouchableOpacity
              style={[styles.restockBtn, { backgroundColor: c.tint }]}
              onPress={(e) => {
                e.stopPropagation();
                handleRestock(item.item_name);
              }}
              disabled={restockingId === item.item_name}>
              <Text style={styles.restockBtnText}>
                {restockingId === item.item_name ? '…' : 'Restock'}
              </Text>
            </TouchableOpacity>
          </TouchableOpacity>
        )}
        ListEmptyComponent={
          <View style={styles.empty}>
            <Text style={[styles.emptyText, { color: c.text }]}>
              No inventory items. They'll appear when the backend has data for this user.
            </Text>
          </View>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
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
  plusIcon: { fontSize: 20 },
  searchWrap: { flexDirection: 'row', alignItems: 'center', margin: 20, position: 'relative' },
  searchIcon: { position: 'absolute', left: 14, zIndex: 1, fontSize: 16 },
  searchInput: {
    flex: 1,
    paddingVertical: 12,
    paddingLeft: 44,
    paddingRight: 16,
    borderRadius: 8,
    borderWidth: 1,
    fontSize: 14,
  },
  tabs: { flexDirection: 'row', gap: 8, paddingHorizontal: 20, paddingBottom: 16 },
  tab: { paddingVertical: 8, paddingHorizontal: 16, borderRadius: 20, borderWidth: 1 },
  tabText: { fontSize: 13 },
  tabTextActive: { fontSize: 13, color: '#fff', fontWeight: '600' },
  errorBox: { marginHorizontal: 20, marginBottom: 8 },
  errorText: { fontSize: 14 },
  listContent: { paddingHorizontal: 20, paddingBottom: 24 },
  inventoryItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    marginBottom: 12,
    gap: 16,
  },
  itemIcon: { width: 50, height: 50, borderRadius: 8, justifyContent: 'center', alignItems: 'center' },
  itemEmoji: { fontSize: 28 },
  itemDetails: { flex: 1 },
  itemName: { fontSize: 15, fontWeight: '600', marginBottom: 4 },
  stockBarBg: { height: 6, borderRadius: 3, overflow: 'hidden', marginBottom: 4 },
  stockBar: { height: '100%', borderRadius: 3 },
  lastBuy: { fontSize: 12, opacity: 0.8 },
  restockBtn: { paddingVertical: 8, paddingHorizontal: 16, borderRadius: 8 },
  restockBtnText: { color: '#fff', fontSize: 12, fontWeight: '600' },
  empty: { padding: 20 },
  emptyText: { fontSize: 15 },
});
