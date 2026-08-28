import { getLocales } from 'expo-localization';
import { StatusBar } from 'expo-status-bar';
import { useEffect, useState } from 'react';
import { ActivityIndicator, FlatList, Modal, Pressable, RefreshControl, SafeAreaView, StyleSheet, Text, useWindowDimensions, View } from 'react-native';
import { WebView } from 'react-native-webview';

type Source = { id: string; name: string; language: string; article_url: string };
type FeedEvent = { id: string; title: string; summary: string; why_it_matters: string | null; category: string; sources: Source[] };
type FeedResponse = { items: FeedEvent[] };
type FeedStatus = 'loading' | 'ready' | 'unavailable';

const apiUrl = process.env.EXPO_PUBLIC_API_URL?.replace(/\/$/, '');
const deviceLanguage = getLocales()[0]?.languageCode ?? 'fr';

export default function App() {
  const { height } = useWindowDimensions();
  const [status, setStatus] = useState<FeedStatus>('loading');
  const [events, setEvents] = useState<FeedEvent[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [sourceEvent, setSourceEvent] = useState<FeedEvent | null>(null);
  const [articleSource, setArticleSource] = useState<Source | null>(null);

  const loadFeed = async (isRefresh = false) => {
    if (!apiUrl) return setStatus('unavailable');
    if (isRefresh) setRefreshing(true); else setStatus('loading');
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 40_000);
    try {
      const response = await fetch(`${apiUrl}/feed?language=${encodeURIComponent(deviceLanguage)}`, { signal: controller.signal });
      if (!response.ok) throw new Error(`Feed request failed with ${response.status}`);
      const feed: FeedResponse = await response.json();
      setEvents(feed.items);
      setStatus('ready');
    } catch {
      setStatus('unavailable');
    } finally {
      clearTimeout(timeout);
      setRefreshing(false);
    }
  };

  useEffect(() => { loadFeed(); }, []);

  if (status !== 'ready') {
    const message = status === 'unavailable'
      ? apiUrl ? 'Le feed est indisponible. Vérifiez le backend, puis réessayez.' : 'Configurez EXPO_PUBLIC_API_URL dans .env'
      : 'Pulseo prépare les dernières actualités…';
    return <View style={styles.centered}>
      {status === 'loading' && <ActivityIndicator color="#A78BFA" size="large" />}
      <Text style={styles.brand}>pulseo</Text><Text style={styles.loadingText}>{message}</Text>
      {status === 'unavailable' && <Pressable onPress={() => loadFeed()} style={styles.retryButton}><Text style={styles.retryText}>Réessayer</Text></Pressable>}
      <StatusBar style="light" />
    </View>;
  }

  return <>
    <FlatList
      data={events}
      keyExtractor={(event) => event.id}
      pagingEnabled
      showsVerticalScrollIndicator={false}
      getItemLayout={(_, index) => ({ length: height, offset: height * index, index })}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => loadFeed(true)} tintColor="#FFFFFF" />}
      renderItem={({ item }) => <NewsCard event={item} height={height} onSources={() => setSourceEvent(item)} />}
    />
    <SourceSheet event={sourceEvent} onClose={() => setSourceEvent(null)} onSelect={setArticleSource} />
    <ArticleViewer source={articleSource} onClose={() => setArticleSource(null)} />
    <StatusBar style="light" />
  </>;
}

function NewsCard({ event, height, onSources }: { event: FeedEvent; height: number; onSources: () => void }) {
  return <View style={[styles.card, { height }]}>
    <View><Text style={styles.eyebrow}>{event.category.toUpperCase()}</Text><Text style={styles.cardBrand}>pulseo</Text></View>
    <View style={styles.story}>
      <Text style={styles.title} numberOfLines={4}>{event.title}</Text>
      <Text style={styles.summary} numberOfLines={9}>{event.summary}</Text>
      {event.why_it_matters ? <Text style={styles.whyItMatters} numberOfLines={3}>Pourquoi c’est important — {event.why_it_matters}</Text> : null}
    </View>
    <View style={styles.footer}>
      <Pressable onPress={onSources} hitSlop={8}>
        <Text style={styles.sources}>Sources : {event.sources.map((source) => source.name).join(' · ')}</Text>
        <Text style={styles.readMore}>Voir les sources et lire l’article</Text>
      </Pressable>
      <Text style={styles.hint}>Faites défiler pour continuer</Text>
    </View>
  </View>;
}

function SourceSheet({ event, onClose, onSelect }: { event: FeedEvent | null; onClose: () => void; onSelect: (source: Source) => void }) {
  return <Modal visible={Boolean(event)} transparent animationType="slide" onRequestClose={onClose}>
    <Pressable style={styles.sheetBackdrop} onPress={onClose}>
      <Pressable style={styles.sheet} onPress={() => undefined}>
        <View style={styles.sheetHandle} /><Text style={styles.sheetTitle}>Cette actualité est couverte par</Text>
        {event?.sources.map((source) => <Pressable key={source.id} onPress={() => { onClose(); onSelect(source); }} style={styles.sourceRow}>
          <View><Text style={styles.sourceName}>{source.name}</Text><Text style={styles.sourceLanguage}>{source.language.toUpperCase()}</Text></View>
          <Text style={styles.openLabel}>Lire ↗</Text>
        </Pressable>)}
      </Pressable>
    </Pressable>
  </Modal>;
}

function ArticleViewer({ source, onClose }: { source: Source | null; onClose: () => void }) {
  return <Modal visible={Boolean(source)} animationType="slide" onRequestClose={onClose}>
    <SafeAreaView style={styles.viewer}>
      <View style={styles.viewerHeader}><Text style={styles.viewerTitle}>{source?.name}</Text><Pressable onPress={onClose} hitSlop={12}><Text style={styles.closeLabel}>Fermer</Text></Pressable></View>
      {source ? <WebView source={{ uri: source.article_url }} startInLoadingState renderLoading={() => <ActivityIndicator style={styles.webLoading} size="large" />} /> : null}
    </SafeAreaView>
  </Modal>;
}

const styles = StyleSheet.create({
  centered: { flex: 1, alignItems: 'center', backgroundColor: '#101014', justifyContent: 'center', padding: 32 },
  brand: { color: '#FFFFFF', fontSize: 44, fontWeight: '800', letterSpacing: -2, marginTop: 24 },
  loadingText: { color: '#A8A8B3', fontSize: 17, marginTop: 8, textAlign: 'center' },
  retryButton: { borderColor: '#A78BFA', borderRadius: 100, borderWidth: 1, marginTop: 28, paddingHorizontal: 20, paddingVertical: 11 }, retryText: { color: '#DDD6FE', fontWeight: '700' },
  card: { backgroundColor: '#101014', justifyContent: 'space-between', overflow: 'hidden', paddingBottom: 44, paddingHorizontal: 28, paddingTop: 62 },
  eyebrow: { color: '#A78BFA', fontSize: 12, fontWeight: '800', letterSpacing: 1.1 }, cardBrand: { color: '#FFFFFF', fontSize: 20, fontWeight: '800', letterSpacing: -1, marginTop: 10 }, story: { paddingVertical: 12 },
  title: { color: '#FFFFFF', fontSize: 30, fontWeight: '800', letterSpacing: -0.8, lineHeight: 36 }, summary: { color: '#E5E5EA', fontSize: 17, lineHeight: 25, marginTop: 18 }, whyItMatters: { color: '#B7AEC9', fontSize: 14, lineHeight: 20, marginTop: 16 },
  footer: { gap: 13 }, sources: { color: '#9CA3AF', fontSize: 13 }, readMore: { color: '#DDD6FE', fontSize: 15, fontWeight: '700', marginTop: 8 }, hint: { color: '#6B7280', fontSize: 12, marginTop: 7 },
  sheetBackdrop: { backgroundColor: 'rgba(0,0,0,0.52)', flex: 1, justifyContent: 'flex-end' }, sheet: { backgroundColor: '#1C1C22', borderTopLeftRadius: 28, borderTopRightRadius: 28, minHeight: 270, padding: 24 }, sheetHandle: { alignSelf: 'center', backgroundColor: '#6B7280', borderRadius: 99, height: 4, marginBottom: 24, width: 42 }, sheetTitle: { color: '#FFFFFF', fontSize: 19, fontWeight: '800', marginBottom: 14 },
  sourceRow: { alignItems: 'center', borderTopColor: '#34343B', borderTopWidth: StyleSheet.hairlineWidth, flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 18 }, sourceName: { color: '#FFFFFF', fontSize: 17, fontWeight: '700' }, sourceLanguage: { color: '#9CA3AF', fontSize: 12, marginTop: 3 }, openLabel: { color: '#C4B5FD', fontSize: 15, fontWeight: '700' },
  viewer: { backgroundColor: '#FFFFFF', flex: 1 }, viewerHeader: { alignItems: 'center', borderBottomColor: '#E5E7EB', borderBottomWidth: StyleSheet.hairlineWidth, flexDirection: 'row', justifyContent: 'space-between', paddingHorizontal: 18, paddingVertical: 14 }, viewerTitle: { color: '#111827', fontSize: 16, fontWeight: '800' }, closeLabel: { color: '#6D28D9', fontSize: 15, fontWeight: '700' }, webLoading: { flex: 1 },
});
