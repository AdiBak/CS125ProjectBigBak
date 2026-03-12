import { useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';
import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';

import Colors from '@/constants/Colors';
import { useColorScheme } from '@/components/useColorScheme';
import {
  getUrgencyLabel,
  restockItem,
  type ProductSuggestion,
} from '@/lib/api';

export default function ProductScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{
    item: string;
    urgency: string;
    reason: string;
    products?: string;
    nearest_store_name?: string;
    nearest_store_address?: string;
  }>();
  const colorScheme = useColorScheme();
  const c = Colors[colorScheme ?? 'light'];

  const urgencyNum = params.urgency ? parseFloat(params.urgency) : 0.5;
  const urgencyLabel = getUrgencyLabel(urgencyNum);
  const products: ProductSuggestion[] = params.products
    ? (JSON.parse(params.products) as ProductSuggestion[])
    : [];
  const primaryProduct = products[0];
  const name = primaryProduct?.name ?? params.item ?? 'Product';
  const price = primaryProduct?.price ?? '—';
  const match = primaryProduct?.relevance;
  const nearestName = (params.nearest_store_name as string) || "Trader Joe's";
  const nearestAddress = (params.nearest_store_address as string) || 'Nearby';

  const [adding, setAdding] = useState(false);

  const handleAddToInventory = async () => {
    const itemKey = params.item ?? name;
    setAdding(true);
    try {
      await restockItem(itemKey);
      router.back();
    } catch {
      setAdding(false);
    } finally {
      setAdding(false);
    }
  };

  const urgencyColor =
    urgencyLabel === 'High' ? c.urgencyHigh : urgencyLabel === 'Medium' ? c.urgencyMedium : c.urgencyLow;

  return (
    <ScrollView style={[styles.container, { backgroundColor: c.background }]} contentContainerStyle={styles.content}>
      <View style={[styles.imagePlaceholder, { backgroundColor: c.border }]}>
        <Text style={styles.imageEmoji}>🛒</Text>
      </View>

      <View style={styles.section}>
        <Text style={[styles.productName, { color: c.text }]}>{name}</Text>
        <Text style={[styles.price, { color: c.price }]}>{price}</Text>
      </View>

      <View style={[styles.card, { backgroundColor: c.cardBg, borderColor: c.border }]}>
        <Text style={[styles.cardTitle, { color: c.text }]}>📊 Why recommended</Text>
        <View style={styles.row}>
          <Text style={[styles.label, { color: c.text }]}>Urgency</Text>
          <Text style={[styles.value, { color: urgencyColor }]}>
            {urgencyNum.toFixed(2)} ({urgencyLabel})
          </Text>
        </View>
        <View style={styles.row}>
          <Text style={[styles.label, { color: c.text }]}>Reason</Text>
          <Text style={[styles.value, { color: c.text }]} numberOfLines={2}>
            {params.reason ?? '—'}
          </Text>
        </View>
        {match && (
          <View style={styles.row}>
            <Text style={[styles.label, { color: c.text }]}>Match score</Text>
            <Text style={[styles.value, { color: c.text }]}>{match}</Text>
          </View>
        )}
      </View>

      <View style={[styles.card, { backgroundColor: c.cardBg, borderColor: c.border }]}>
        <Text style={[styles.cardTitle, { color: c.text }]}>📍 Nearby store</Text>
        <View style={[styles.storeRow, { borderColor: c.border }]}>
          <View>
            <Text style={[styles.storeName, { color: c.text }]}>{nearestName}</Text>
            <Text style={[styles.storeDistance, { color: c.text, opacity: 0.8 }]}>
              {nearestAddress}
            </Text>
          </View>
        </View>
      </View>

      {products.length > 0 && (
        <View style={[styles.card, { backgroundColor: c.cardBg, borderColor: c.border }]}>
          <Text style={[styles.cardTitle, { color: c.text }]}>💡 Similar products</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.similarList}>
            {products.map((p, i) => (
              <View key={i} style={[styles.similarItem, { backgroundColor: c.background }]}>
                <Text style={styles.similarEmoji}>🛒</Text>
                <Text style={[styles.similarName, { color: c.text }]} numberOfLines={2}>
                  {p.name}
                </Text>
                <Text style={[styles.similarPrice, { color: c.price }]}>{p.price}</Text>
              </View>
            ))}
          </ScrollView>
        </View>
      )}

      <View style={styles.actions}>
        <TouchableOpacity
          style={[styles.addBtn, { backgroundColor: c.tint }]}
          onPress={handleAddToInventory}
          disabled={adding}>
          {adding ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.addBtnText}>Add to Inventory</Text>
          )}
        </TouchableOpacity>
      </View>

      <View style={{ height: 40 }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { paddingBottom: 24 },
  imagePlaceholder: {
    height: 220,
    justifyContent: 'center',
    alignItems: 'center',
  },
  imageEmoji: { fontSize: 80 },
  section: { padding: 20 },
  productName: { fontSize: 24, fontWeight: '700', marginBottom: 8 },
  price: { fontSize: 28, fontWeight: '700' },
  card: {
    marginHorizontal: 20,
    marginBottom: 16,
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
  },
  cardTitle: { fontSize: 14, fontWeight: '600', marginBottom: 12 },
  row: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 },
  label: { fontSize: 13, flex: 1 },
  value: { fontSize: 13, fontWeight: '600', flex: 1 },
  storeRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
  },
  storeName: { fontSize: 14, fontWeight: '600' },
  storeDistance: { fontSize: 13 },
  similarList: { marginHorizontal: -4 },
  similarItem: {
    width: 110,
    padding: 12,
    borderRadius: 8,
    marginRight: 12,
    alignItems: 'center',
  },
  similarEmoji: { fontSize: 36, marginBottom: 8 },
  similarName: { fontSize: 12, fontWeight: '600', textAlign: 'center' },
  similarPrice: { fontSize: 12, marginTop: 4 },
  actions: { paddingHorizontal: 20, marginTop: 16 },
  addBtn: {
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
  },
  addBtnText: { color: '#fff', fontWeight: '600', fontSize: 16 },
});
