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
import { setInventoryItem } from '@/lib/api';

export default function EditInventoryItemScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{
    item_name: string;
    stock_percentage: string;
    last_bought_days_ago: string;
  }>();
  const colorScheme = useColorScheme();
  const c = Colors[colorScheme ?? 'light'];

  const itemName = params.item_name ?? '';
  const [stockPct, setStockPct] = useState(
    params.stock_percentage ? parseFloat(params.stock_percentage) : 100
  );
  const [daysAgo, setDaysAgo] = useState(
    params.last_bought_days_ago ? parseInt(params.last_bought_days_ago, 10) : 0
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const stock = Math.round(stockPct) / 100;
  const handleSave = async () => {
    if (!itemName) return;
    setError(null);
    setSaving(true);
    try {
      await setInventoryItem(itemName, stock, daysAgo);
      router.back();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  if (!itemName) {
    return (
      <View style={[styles.container, { backgroundColor: c.background }]}>
        <Text style={[styles.error, { color: c.text }]}>Missing item name.</Text>
      </View>
    );
  }

  const stockPresets = [
    { label: 'Low', pct: 20 },
    { label: 'Medium', pct: 50 },
    { label: 'High', pct: 80 },
    { label: 'Full', pct: 100 },
  ];

  return (
    <ScrollView style={[styles.container, { backgroundColor: c.background }]} contentContainerStyle={styles.content}>
      <View style={styles.section}>
        <Text style={[styles.itemName, { color: c.text }]}>{itemName}</Text>
      </View>

      <View style={[styles.card, { backgroundColor: c.cardBg, borderColor: c.border }]}>
        <Text style={[styles.label, { color: c.text }]}>
          Stock level: {Math.round(stockPct)}%
        </Text>
        <View style={styles.stockRow}>
          <TouchableOpacity
            style={[styles.stepperBtn, { backgroundColor: c.tint }]}
            onPress={() => setStockPct((s) => Math.max(0, s - 10))}>
            <Text style={styles.stepperText}>−10</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.stepperBtn, { backgroundColor: c.tint }]}
            onPress={() => setStockPct((s) => Math.min(100, s + 10))}>
            <Text style={styles.stepperText}>+10</Text>
          </TouchableOpacity>
        </View>
        <View style={styles.presetsRow}>
          {stockPresets.map(({ label, pct }) => (
            <TouchableOpacity
              key={label}
              style={[
                styles.presetBtn,
                { backgroundColor: c.background, borderColor: c.border },
                Math.round(stockPct) === pct && { backgroundColor: c.tint, borderColor: c.tint },
              ]}
              onPress={() => setStockPct(pct)}>
              <Text
                style={[
                  styles.presetText,
                  { color: c.text },
                  Math.round(stockPct) === pct && { color: '#fff' },
                ]}>
                {label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      <View style={[styles.card, { backgroundColor: c.cardBg, borderColor: c.border }]}>
        <Text style={[styles.label, { color: c.text }]}>
          Days since last purchase: {daysAgo}
        </Text>
        <View style={styles.daysRow}>
          <TouchableOpacity
            style={[styles.daysBtn, { backgroundColor: c.tint }]}
            onPress={() => setDaysAgo((d) => Math.max(0, d - 1))}>
            <Text style={styles.daysBtnText}>−</Text>
          </TouchableOpacity>
          <Text style={[styles.daysValue, { color: c.text }]}>{daysAgo}</Text>
          <TouchableOpacity
            style={[styles.daysBtn, { backgroundColor: c.tint }]}
            onPress={() => setDaysAgo((d) => d + 1)}>
            <Text style={styles.daysBtnText}>+</Text>
          </TouchableOpacity>
        </View>
      </View>

      {error ? <Text style={[styles.error, { color: c.urgencyHigh }]}>{error}</Text> : null}

      <TouchableOpacity
        style={[styles.saveBtn, { backgroundColor: c.tint }]}
        onPress={handleSave}
        disabled={saving}>
        {saving ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.saveBtnText}>Save</Text>
        )}
      </TouchableOpacity>

      <Text style={[styles.hint, { color: c.text }]}>
        Lower stock or increase days ago to see this item on Home again.
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { padding: 24, paddingBottom: 48 },
  section: { marginBottom: 24 },
  itemName: { fontSize: 22, fontWeight: '700' },
  card: {
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    marginBottom: 16,
  },
  label: { fontSize: 16, fontWeight: '600', marginBottom: 12 },
  stockRow: { flexDirection: 'row', gap: 12, marginBottom: 12 },
  stepperBtn: { flex: 1, padding: 12, borderRadius: 8, alignItems: 'center' },
  stepperText: { color: '#fff', fontWeight: '600' },
  presetsRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  presetBtn: { paddingVertical: 8, paddingHorizontal: 16, borderRadius: 8, borderWidth: 1 },
  presetText: { fontSize: 14, fontWeight: '600' },
  daysRow: { flexDirection: 'row', alignItems: 'center', gap: 16 },
  daysBtn: { width: 44, height: 44, borderRadius: 22, justifyContent: 'center', alignItems: 'center' },
  daysBtnText: { color: '#fff', fontSize: 24, fontWeight: '600' },
  daysValue: { fontSize: 20, fontWeight: '600', minWidth: 40, textAlign: 'center' },
  error: { fontSize: 14, marginBottom: 12 },
  saveBtn: { padding: 16, borderRadius: 12, alignItems: 'center', marginTop: 8 },
  saveBtnText: { color: '#fff', fontWeight: '600', fontSize: 16 },
  hint: { fontSize: 13, marginTop: 16, opacity: 0.8 },
});
