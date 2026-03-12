import { useRouter } from 'expo-router';
import { useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';

import Colors from '@/constants/Colors';
import { useColorScheme } from '@/components/useColorScheme';
import { restockItem } from '@/lib/api';

export default function AddItemScreen() {
  const router = useRouter();
  const colorScheme = useColorScheme();
  const c = Colors[colorScheme ?? 'light'];
  const [itemName, setItemName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAdd = async () => {
    const name = itemName.trim();
    if (!name) return;
    setError(null);
    setLoading(true);
    try {
      await restockItem(name);
      router.back();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to add item');
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={[styles.container, { backgroundColor: c.background }]}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <View style={styles.inner}>
        <Text style={[styles.label, { color: c.text }]}>Item name</Text>
        <TextInput
          style={[styles.input, { backgroundColor: c.cardBg, color: c.text, borderColor: c.border }]}
          placeholder="e.g. Milk, Eggs, Cheese"
          placeholderTextColor="#95a5a6"
          value={itemName}
          onChangeText={setItemName}
          autoCapitalize="words"
          editable={!loading}
        />
        {error ? <Text style={[styles.error, { color: c.urgencyHigh }]}>{error}</Text> : null}
        <TouchableOpacity
          style={[styles.button, { backgroundColor: c.tint }]}
          onPress={handleAdd}
          disabled={!itemName.trim() || loading}>
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.buttonText}>Add to inventory</Text>
          )}
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  inner: { flex: 1, padding: 24, justifyContent: 'center' },
  label: { fontSize: 16, fontWeight: '600', marginBottom: 8 },
  input: {
    borderWidth: 1,
    borderRadius: 12,
    padding: 16,
    fontSize: 16,
    marginBottom: 16,
  },
  error: { fontSize: 14, marginBottom: 12 },
  stockRow: { flexDirection: 'row', gap: 12, marginBottom: 24 },
  stockOption: {
    flex: 1,
    padding: 12,
    borderRadius: 12,
    borderWidth: 1,
    alignItems: 'center',
  },
  stockOptionText: { fontSize: 15, fontWeight: '600' },
  stockOptionSub: { fontSize: 11, marginTop: 4, opacity: 0.8 },
  button: { padding: 16, borderRadius: 12, alignItems: 'center' },
  buttonText: { color: '#fff', fontWeight: '600', fontSize: 16 },
});
