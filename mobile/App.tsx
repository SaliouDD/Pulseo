import { StatusBar } from 'expo-status-bar';
import { useEffect, useState } from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';

type HealthStatus = 'checking' | 'connected' | 'unavailable';

const apiUrl = process.env.EXPO_PUBLIC_API_URL?.replace(/\/$/, '');

export default function App() {
  const [status, setStatus] = useState<HealthStatus>('checking');

  useEffect(() => {
    if (!apiUrl) {
      setStatus('unavailable');
      return;
    }

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5_000);

    fetch(`${apiUrl}/health`, { signal: controller.signal })
      .then((response) => {
        setStatus(response.ok ? 'connected' : 'unavailable');
      })
      .catch(() => setStatus('unavailable'))
      .finally(() => clearTimeout(timeout));

    return () => {
      clearTimeout(timeout);
      controller.abort();
    };
  }, []);

  const message =
    status === 'connected'
      ? 'API Pulseo connectée'
      : status === 'unavailable'
        ? apiUrl
          ? 'API indisponible — vérifiez l’adresse et le backend'
          : 'Configurez EXPO_PUBLIC_API_URL dans .env'
        : 'Connexion à l’API…';

  return (
    <View style={styles.container}>
      <Text style={styles.brand}>pulseo</Text>
      <Text style={styles.tagline}>L’actualité, claire et essentielle.</Text>
      <View style={styles.status}>
        {status === 'checking' && <ActivityIndicator color="#8B5CF6" />}
        <View style={[styles.dot, status === 'connected' ? styles.dotOnline : styles.dotOffline]} />
        <Text style={styles.statusText}>{message}</Text>
      </View>
      <StatusBar style="light" />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#101014',
    justifyContent: 'center',
    padding: 32,
  },
  brand: {
    color: '#FFFFFF',
    fontSize: 44,
    fontWeight: '800',
    letterSpacing: -2,
  },
  tagline: {
    color: '#A8A8B3',
    fontSize: 17,
    marginTop: 8,
  },
  status: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 10,
    marginTop: 42,
  },
  dot: {
    borderRadius: 5,
    height: 10,
    width: 10,
  },
  dotOnline: {
    backgroundColor: '#34D399',
  },
  dotOffline: {
    backgroundColor: '#F87171',
  },
  statusText: {
    color: '#D1D1D8',
    flex: 1,
    fontSize: 15,
  },
});
