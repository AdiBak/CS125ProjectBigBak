import { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  View,
} from 'react-native';

import Colors from '@/constants/Colors';
import { useColorScheme } from '@/components/useColorScheme';
import { getUserSettings, type UserSettings } from '@/lib/api';

export default function SettingsScreen() {
  const colorScheme = useColorScheme();
  const c = Colors[colorScheme];
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getUserSettings()
      .then((data) => {
        if (!cancelled) setSettings(data);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load settings');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return (
      <View style={[styles.centered, { backgroundColor: c.background }]}>
        <ActivityIndicator size="large" color={c.tint} />
      </View>
    );
  }

  return (
    <ScrollView style={[styles.container, { backgroundColor: c.background }]} contentContainerStyle={styles.content}>
      <View style={[styles.header, { backgroundColor: c.tint }]}>
        <Text style={styles.headerTitle}>Settings</Text>
      </View>

      {error ? (
        <View style={styles.errorBox}>
          <Text style={[styles.errorText, { color: c.text }]}>{error}</Text>
        </View>
      ) : null}

      {settings ? (
        <>
          <View style={styles.section}>
            <Text style={[styles.sectionTitle, { color: c.text }]}>User Profile</Text>
            <Row label="Name" value={settings.user_name} colors={c} />
            <Row label="Email" value={settings.email} colors={c} />
          </View>

          <View style={styles.section}>
            <Text style={[styles.sectionTitle, { color: c.text }]}>Shopping Preferences</Text>
            <Row label="Preferred Brands" value={settings.preferred_brands?.join(', ') || '—'} colors={c} />
            <Row label="Price Sensitivity" value={settings.price_sensitivity} colors={c} />
          </View>

          <View style={styles.section}>
            <Text style={[styles.sectionTitle, { color: c.text }]}>Notifications</Text>
            <RowSwitch label="Location-based alerts" value={settings.location_alerts} colors={c} />
            <RowSwitch label="Low stock warnings" value={settings.low_stock_warnings} colors={c} />
          </View>
        </>
      ) : null}

      <View style={{ height: 32 }} />
    </ScrollView>
  );
}

function Row({
  label,
  value,
  colors,
}: {
  label: string;
  value: string;
  colors: typeof Colors.light;
}) {
  return (
    <View style={[styles.row, { backgroundColor: colors.cardBg, borderColor: colors.border }]}>
      <Text style={[styles.rowLabel, { color: colors.text }]}>{label}</Text>
      <Text style={[styles.rowValue, { color: colors.text }]}>{value} →</Text>
    </View>
  );
}

function RowSwitch({
  label,
  value,
  colors,
}: {
  label: string;
  value: boolean;
  colors: typeof Colors.light;
}) {
  return (
    <View style={[styles.row, { backgroundColor: colors.cardBg, borderColor: colors.border }]}>
      <Text style={[styles.rowLabel, { color: colors.text }]}>{label}</Text>
      <Switch value={value} trackColor={{ false: '#bdc3c7', true: colors.tint }} thumbColor="#fff" />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { paddingBottom: 24 },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: {
    paddingHorizontal: 20,
    paddingVertical: 16,
    paddingTop: 48,
  },
  headerTitle: { fontSize: 24, fontWeight: '600', color: '#fff' },
  errorBox: { margin: 20 },
  errorText: { fontSize: 14 },
  section: { marginHorizontal: 20, marginTop: 24 },
  sectionTitle: {
    fontSize: 13,
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 12,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderRadius: 8,
    borderWidth: 1,
    marginBottom: 8,
  },
  rowLabel: { fontSize: 15 },
  rowValue: { fontSize: 14, opacity: 0.8 },
});
