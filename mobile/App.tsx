import { StatusBar } from 'expo-status-bar';
import { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Linking,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from 'react-native';

type Source = {
  id: string;
  name: string;
  language: string;
  article_url: string;
};

type FeedEvent = {
  id: string;
  title: string;
  summary: string;
  why_it_matters: string | null;
  category: string;
  topics: string[];
  sources: Source[];
};

type FeedResponse = {
  items: FeedEvent[];
};

type FeedStatus = 'loading' | 'ready' | 'unavailable';

const apiUrl = process.env.EXPO_PUBLIC_API_URL?.replace(/\/$/, '');

export default function App() {
  const [status, setStatus] = useState<FeedStatus>('loading');
  const [events, setEvents] = useState<FeedEvent[]>([]);

  const loadFeed = async () => {
    if (!apiUrl) {
      setStatus('unavailable');
      return;
    }

    setStatus('loading');
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 40_000);

    try {
      const response = await fetch(`${apiUrl}/feed`, { signal: controller.signal });
      if (!response.ok) {
        throw new Error(`Feed request failed with ${response.status}`);
      }
      const feed: FeedResponse = await response.json();
      setEvents(feed.items);
      setStatus('ready');
    } catch {
      setStatus('unavailable');
    } finally {
      clearTimeout(timeout);
    }
  };

  useEffect(() => {
    loadFeed();
  }, []);

  if (status !== 'ready') {
    const message =
      status === 'unavailable'
        ? apiUrl
          ? 'Le feed est indisponible. Vérifiez que le backend est démarré, puis réessayez.'
          : 'Configurez EXPO_PUBLIC_API_URL dans .env'
        : 'Pulseo prépare les dernières actualités…';

    return (
      <View style={styles.centered}>
        {status === 'loading' && <ActivityIndicator color="#A78BFA" size="large" />}
        <Text style={styles.brand}>pulseo</Text>
        <Text style={styles.loadingText}>{message}</Text>
        {status === 'unavailable' && (
          <Pressable onPress={loadFeed} style={styles.retryButton}>
            <Text style={styles.retryText}>Réessayer</Text>
          </Pressable>
        )}
        <StatusBar style="light" />
      </View>
    );
  }

  return (
    <>
      <FlatList
        data={events}
        keyExtractor={(event) => event.id}
        pagingEnabled
        showsVerticalScrollIndicator={false}
        refreshControl={<RefreshControl refreshing={false} onRefresh={loadFeed} tintColor="#FFFFFF" />}
        renderItem={({ item }) => <NewsCard event={item} />}
      />
      <StatusBar style="light" />
    </>
  );
}

function NewsCard({ event }: { event: FeedEvent }) {
  const primarySource = event.sources[0];

  return (
    <View style={styles.card}>
      <View>
        <Text style={styles.eyebrow}>{event.category.toUpperCase()}</Text>
        <Text style={styles.cardBrand}>pulseo</Text>
      </View>
      <View>
        <Text style={styles.title}>{event.title}</Text>
        <Text style={styles.summary}>{event.summary}</Text>
        {event.why_it_matters ? (
          <Text style={styles.whyItMatters}>Pourquoi c’est important — {event.why_it_matters}</Text>
        ) : null}
      </View>
      <View style={styles.footer}>
        <Text style={styles.sources}>Sources : {event.sources.map((source) => source.name).join(' · ')}</Text>
        <Pressable onPress={() => Linking.openURL(primarySource.article_url)} hitSlop={8}>
          <Text style={styles.readMore}>Lire l’article ↗</Text>
        </Pressable>
        <Text style={styles.hint}>Faites défiler pour continuer</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  centered: {
    flex: 1,
    backgroundColor: '#101014',
    justifyContent: 'center',
    padding: 32,
    alignItems: 'center',
  },
  brand: {
    color: '#FFFFFF',
    fontSize: 44,
    fontWeight: '800',
    letterSpacing: -2,
    marginTop: 24,
  },
  loadingText: {
    color: '#A8A8B3',
    fontSize: 17,
    marginTop: 8,
    textAlign: 'center',
  },
  retryButton: {
    borderColor: '#A78BFA',
    borderRadius: 100,
    borderWidth: 1,
    marginTop: 28,
    paddingHorizontal: 20,
    paddingVertical: 11,
  },
  retryText: {
    color: '#DDD6FE',
    fontWeight: '700',
  },
  card: {
    backgroundColor: '#101014',
    flex: 1,
    justifyContent: 'space-between',
    paddingHorizontal: 28,
    paddingTop: 70,
    paddingBottom: 48,
  },
  eyebrow: {
    color: '#A78BFA',
    fontSize: 12,
    fontWeight: '800',
    letterSpacing: 1.1,
  },
  cardBrand: {
    color: '#FFFFFF',
    fontSize: 20,
    fontWeight: '800',
    letterSpacing: -1,
    marginTop: 10,
  },
  title: {
    color: '#FFFFFF',
    fontSize: 31,
    fontWeight: '800',
    letterSpacing: -0.8,
    lineHeight: 37,
  },
  summary: {
    color: '#E5E5EA',
    fontSize: 18,
    lineHeight: 27,
    marginTop: 20,
  },
  whyItMatters: {
    color: '#B7AEC9',
    fontSize: 14,
    lineHeight: 20,
    marginTop: 18,
  },
  footer: {
    gap: 13,
  },
  sources: {
    color: '#9CA3AF',
    fontSize: 13,
  },
  readMore: {
    color: '#DDD6FE',
    fontSize: 15,
    fontWeight: '700',
  },
  hint: {
    color: '#6B7280',
    fontSize: 12,
    marginTop: 7,
  },
});
