import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
  Linking,
  ScrollView,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../../utils/colors';
import api from '../../utils/api';
import { format } from 'date-fns';
import { useTranslation } from 'react-i18next';

interface NewsArticle {
  id: string;
  title: string;
  description?: string;
  summary?: string;
  content?: string;
  source: string;
  url: string;
  project_name?: string;
  location?: string;
  issue_type?: string;
  category?: string;
  severity?: string;
  relevance_score?: number;
  published_date?: string;
  published_at?: string;
}

const SEVERITY_COLORS = {
  high: colors.error,
  medium: colors.warning,
  low: colors.info,
};

const ISSUE_ICONS: { [key: string]: string } = {
  stuck: 'alert-circle',
  underperforming: 'trending-down',
  opportunity: 'rocket',
  general: 'newspaper',
  'Project Issues': 'alert-circle',
  'New Projects': 'add-circle',
  'Tenders & Contracts': 'document-text',
  'Market Analysis': 'analytics',
  'Regulations': 'shield-checkmark',
  'Sustainability': 'leaf',
  'Technology': 'hardware-chip',
  'General': 'newspaper',
};

const PROJECT_TYPOLOGIES = [
  'Alle', 'Wohnungsbau', 'Gewerbebau', 'Infrastruktur', 
  'Gesundheitswesen', 'Bildung', 'Industrie'
];

export default function NewsScreen() {
  const [news, setNews] = useState<NewsArticle[]>([]);
  const [filteredNews, setFilteredNews] = useState<NewsArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedTypology, setSelectedTypology] = useState('Alle');
  const router = useRouter();
  const { t } = useTranslation();

  useEffect(() => {
    fetchNews();
  }, []);

  const fetchNews = async () => {
    try {
      const response = await api.get('/news');
      setNews(response.data);
    } catch (error) {
      console.error('Failed to fetch news:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchNews();
  }, []);

  const openArticle = (url: string) => {
    Linking.openURL(url);
  };

  const renderNewsCard = ({ item }: { item: NewsArticle }) => (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <View style={styles.badges}>
          <View
            style={[
              styles.severityBadge,
              { backgroundColor: SEVERITY_COLORS[item.severity as keyof typeof SEVERITY_COLORS] },
            ]}
          >
            <Text style={styles.severityText}>
              {t(`news.severity.${item.severity}`)}
            </Text>
          </View>
          <View style={styles.typeBadge}>
            <Ionicons
              name={ISSUE_ICONS[(item.issue_type || item.category || 'General') as keyof typeof ISSUE_ICONS] || 'newspaper'}
              size={14}
              color={colors.primary}
            />
            <Text style={styles.typeText}>
              {item.category || item.issue_type || 'News'}
            </Text>
          </View>
        </View>
        <Text style={styles.dateText}>
          {item.published_at ? format(new Date(item.published_at), 'dd MMM yyyy') : 
           item.published_date ? format(new Date(item.published_date), 'dd MMM yyyy') : 'Recent'}
        </Text>
      </View>

      <Text style={styles.cardTitle} numberOfLines={2}>
        {item.title}
      </Text>

      {item.project_name && (
        <View style={styles.projectInfo}>
          <Ionicons name="construct" size={16} color={colors.primary} />
          <Text style={styles.projectName}>{item.project_name}</Text>
        </View>
      )}

      {item.location && (
        <View style={styles.locationInfo}>
          <Ionicons name="location" size={16} color={colors.textLight} />
          <Text style={styles.locationText}>{item.location}</Text>
        </View>
      )}

      <Text style={styles.cardDescription} numberOfLines={3}>
        {item.description}
      </Text>

      <View style={styles.cardFooter}>
        <View style={styles.sourceContainer}>
          <Ionicons name="newspaper-outline" size={14} color={colors.textLight} />
          <Text style={styles.sourceText}>{item.source}</Text>
        </View>
        <TouchableOpacity
          style={styles.readMoreButton}
          onPress={() => openArticle(item.url)}
        >
          <Text style={styles.readMoreText}>{t('news.readMore')}</Text>
          <Ionicons name="arrow-forward" size={16} color={colors.secondary} />
        </TouchableOpacity>
      </View>
    </View>
  );

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={news}
        renderItem={renderNewsCard}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.list}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor={colors.primary}
          />
        }
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Ionicons name="newspaper-outline" size={64} color={colors.textLight} />
            <Text style={styles.emptyText}>{t('news.noNews')}</Text>
          </View>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  list: {
    padding: 16,
  },
  card: {
    backgroundColor: colors.card,
    borderRadius: 16,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  badges: {
    flexDirection: 'row',
    gap: 8,
  },
  severityBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  severityText: {
    fontSize: 11,
    color: colors.textWhite,
    fontWeight: '600',
  },
  typeBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.background,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
    gap: 4,
  },
  typeText: {
    fontSize: 11,
    color: colors.primary,
    fontWeight: '600',
  },
  dateText: {
    fontSize: 12,
    color: colors.textLight,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: colors.text,
    marginBottom: 8,
  },
  projectInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 6,
    gap: 6,
  },
  projectName: {
    fontSize: 14,
    color: colors.primary,
    fontWeight: '600',
  },
  locationInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
    gap: 6,
  },
  locationText: {
    fontSize: 13,
    color: colors.textLight,
  },
  cardDescription: {
    fontSize: 14,
    color: colors.text,
    lineHeight: 20,
    marginBottom: 12,
  },
  cardFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  sourceContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  sourceText: {
    fontSize: 12,
    color: colors.textLight,
  },
  readMoreButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  readMoreText: {
    fontSize: 14,
    color: colors.secondary,
    fontWeight: '600',
  },
  emptyContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 64,
  },
  emptyText: {
    fontSize: 16,
    color: colors.textLight,
    marginTop: 16,
  },
});