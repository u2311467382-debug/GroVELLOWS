import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
  Platform,
  ScrollView,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../../utils/colors';
import api from '../../utils/api';
import { format } from 'date-fns';

interface Tender {
  id: string;
  title: string;
  description: string;
  budget: string;
  deadline: string;
  location: string;
  project_type: string;
  category: string;
  status: string;
  platform_source: string;
  direct_link?: string;
}

interface SharedTender {
  id: string;
  tender_id: string;
  tender?: Tender;
  shared_by: string;
  shared_by_name?: string;
  message?: string;
  created_at: string;
}

const STATUS_COLORS = {
  'New': colors.success,
  'In Progress': colors.warning,
  'Closed': colors.textLight,
};

export default function FavoritesScreen() {
  const [favorites, setFavorites] = useState<Tender[]>([]);
  const [sharedTenders, setSharedTenders] = useState<SharedTender[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState<'favorites' | 'shared'>('favorites');
  const router = useRouter();

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [favResponse, sharedResponse] = await Promise.all([
        api.get('/favorites'),
        api.get('/shares')
      ]);
      setFavorites(favResponse.data);
      
      // Fetch tender details for shared tenders
      const sharedWithDetails = await Promise.all(
        sharedResponse.data.map(async (share: SharedTender) => {
          try {
            const tenderResponse = await api.get(`/tenders/${share.tender_id}`);
            return { ...share, tender: tenderResponse.data };
          } catch (e) {
            return share;
          }
        })
      );
      setSharedTenders(sharedWithDetails);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchData();
  }, []);

  const renderTenderCard = ({ item }: { item: Tender }) => (
    <TouchableOpacity
      style={styles.card}
      onPress={() => router.push(`/tender/${item.id}`)}
    >
      <View style={styles.cardHeader}>
        <View style={styles.statusBadge}>
          <View
            style={[
              styles.statusDot,
              { backgroundColor: STATUS_COLORS[item.status as keyof typeof STATUS_COLORS] || colors.textLight },
            ]}
          />
          <Text style={styles.statusText}>{item.status || 'New'}</Text>
        </View>
        <View style={styles.categoryBadge}>
          <Text style={styles.categoryText}>{item.category}</Text>
        </View>
      </View>

      <Text style={styles.cardTitle} numberOfLines={2}>
        {item.title}
      </Text>
      <Text style={styles.cardDescription} numberOfLines={2}>
        {item.description}
      </Text>

      <View style={styles.cardDetails}>
        <View style={styles.detailRow}>
          <Ionicons name="location-outline" size={16} color={colors.textLight} />
          <Text style={styles.detailText}>{item.location}</Text>
        </View>
        <View style={styles.detailRow}>
          <Ionicons name="cash-outline" size={16} color={colors.textLight} />
          <Text style={styles.detailText}>{item.budget}</Text>
        </View>
        <View style={styles.detailRow}>
          <Ionicons name="calendar-outline" size={16} color={colors.textLight} />
          <Text style={styles.detailText}>
            {item.deadline ? format(new Date(item.deadline), 'dd MMM yyyy') : 'No deadline'}
          </Text>
        </View>
      </View>

      <View style={styles.cardFooter}>
        <Text style={styles.platformText}>{item.platform_source}</Text>
        <Ionicons name="chevron-forward" size={20} color={colors.primary} />
      </View>
    </TouchableOpacity>
  );

  const renderSharedCard = ({ item }: { item: SharedTender }) => {
    const tender = item.tender;
    if (!tender) {
      return (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Tender not available</Text>
          <Text style={styles.sharedByText}>
            Shared by {item.shared_by_name || 'Team member'}
          </Text>
        </View>
      );
    }

    return (
      <TouchableOpacity
        style={styles.card}
        onPress={() => router.push(`/tender/${tender.id}`)}
      >
        {/* Shared Info Banner */}
        <View style={styles.sharedBanner}>
          <Ionicons name="share-social" size={16} color={colors.primary} />
          <Text style={styles.sharedByText}>
            Shared by {item.shared_by_name || 'Team member'}
          </Text>
          <Text style={styles.sharedDateText}>
            {format(new Date(item.created_at), 'dd MMM yyyy HH:mm')}
          </Text>
        </View>

        {item.message && (
          <View style={styles.messageContainer}>
            <Ionicons name="chatbubble-outline" size={14} color={colors.textLight} />
            <Text style={styles.messageText}>"{item.message}"</Text>
          </View>
        )}

        <View style={styles.cardHeader}>
          <View style={styles.statusBadge}>
            <View
              style={[
                styles.statusDot,
                { backgroundColor: STATUS_COLORS[tender.status as keyof typeof STATUS_COLORS] || colors.textLight },
              ]}
            />
            <Text style={styles.statusText}>{tender.status || 'New'}</Text>
          </View>
          <View style={styles.categoryBadge}>
            <Text style={styles.categoryText}>{tender.category}</Text>
          </View>
        </View>

        <Text style={styles.cardTitle} numberOfLines={2}>
          {tender.title}
        </Text>
        <Text style={styles.cardDescription} numberOfLines={2}>
          {tender.description}
        </Text>

        <View style={styles.cardDetails}>
          <View style={styles.detailRow}>
            <Ionicons name="location-outline" size={16} color={colors.textLight} />
            <Text style={styles.detailText}>{tender.location}</Text>
          </View>
          <View style={styles.detailRow}>
            <Ionicons name="cash-outline" size={16} color={colors.textLight} />
            <Text style={styles.detailText}>{tender.budget}</Text>
          </View>
          <View style={styles.detailRow}>
            <Ionicons name="calendar-outline" size={16} color={colors.textLight} />
            <Text style={styles.detailText}>
              {tender.deadline ? format(new Date(tender.deadline), 'dd MMM yyyy') : 'No deadline'}
            </Text>
          </View>
        </View>

        <View style={styles.cardFooter}>
          <Text style={styles.platformText}>{tender.platform_source}</Text>
          <Ionicons name="chevron-forward" size={20} color={colors.primary} />
        </View>
      </TouchableOpacity>
    );
  };

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Tab Selector */}
      <View style={styles.tabContainer}>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'favorites' && styles.tabActive]}
          onPress={() => setActiveTab('favorites')}
        >
          <Ionicons 
            name="star" 
            size={18} 
            color={activeTab === 'favorites' ? colors.accent : colors.textLight} 
          />
          <Text style={[styles.tabText, activeTab === 'favorites' && styles.tabTextActive]}>
            Favorites ({favorites.length})
          </Text>
        </TouchableOpacity>
        
        <TouchableOpacity
          style={[styles.tab, activeTab === 'shared' && styles.tabActive]}
          onPress={() => setActiveTab('shared')}
        >
          <Ionicons 
            name="share-social" 
            size={18} 
            color={activeTab === 'shared' ? colors.accent : colors.textLight} 
          />
          <Text style={[styles.tabText, activeTab === 'shared' && styles.tabTextActive]}>
            Shared ({sharedTenders.length})
          </Text>
          {sharedTenders.length > 0 && (
            <View style={styles.badge}>
              <Text style={styles.badgeText}>{sharedTenders.length}</Text>
            </View>
          )}
        </TouchableOpacity>
      </View>

      {activeTab === 'favorites' ? (
        <FlatList
          data={favorites}
          renderItem={renderTenderCard}
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
              <Ionicons name="star-outline" size={64} color={colors.textLight} />
              <Text style={styles.emptyText}>No favorites yet</Text>
              <Text style={styles.emptySubtext}>
                Star tenders to save them here
              </Text>
            </View>
          }
        />
      ) : (
        <FlatList
          data={sharedTenders}
          renderItem={renderSharedCard}
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
              <Ionicons name="share-social-outline" size={64} color={colors.textLight} />
              <Text style={styles.emptyText}>No shared tenders</Text>
              <Text style={styles.emptySubtext}>
                Tenders shared by your team will appear here
              </Text>
            </View>
          }
        />
      )}
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
  tabContainer: {
    flexDirection: 'row',
    backgroundColor: colors.card,
    padding: 8,
    marginHorizontal: 16,
    marginTop: 16,
    borderRadius: 12,
  },
  tab: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 12,
    borderRadius: 8,
    gap: 6,
  },
  tabActive: {
    backgroundColor: colors.primary,
  },
  tabText: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.textLight,
  },
  tabTextActive: {
    color: colors.accent,
  },
  badge: {
    backgroundColor: colors.error,
    borderRadius: 10,
    minWidth: 20,
    height: 20,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 6,
    marginLeft: 4,
  },
  badgeText: {
    color: colors.textWhite,
    fontSize: 12,
    fontWeight: 'bold',
  },
  list: {
    padding: 16,
  },
  card: {
    backgroundColor: colors.card,
    borderRadius: 16,
    padding: 16,
    marginBottom: 16,
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 4,
      },
      android: {
        elevation: 3,
      },
      web: {
        boxShadow: '0px 2px 4px rgba(0, 0, 0, 0.1)',
      },
    }),
  },
  sharedBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.primaryLight,
    padding: 10,
    borderRadius: 8,
    marginBottom: 12,
    gap: 8,
  },
  sharedByText: {
    flex: 1,
    fontSize: 13,
    color: colors.primary,
    fontWeight: '600',
  },
  sharedDateText: {
    fontSize: 12,
    color: colors.textLight,
  },
  messageContainer: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    backgroundColor: colors.background,
    padding: 10,
    borderRadius: 8,
    marginBottom: 12,
    gap: 8,
  },
  messageText: {
    flex: 1,
    fontSize: 13,
    color: colors.text,
    fontStyle: 'italic',
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.background,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 6,
  },
  statusText: {
    fontSize: 12,
    color: colors.text,
    fontWeight: '600',
  },
  categoryBadge: {
    backgroundColor: colors.primaryLight,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
  },
  categoryText: {
    fontSize: 12,
    color: colors.accent,
    fontWeight: '600',
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: colors.text,
    marginBottom: 8,
  },
  cardDescription: {
    fontSize: 14,
    color: colors.textLight,
    marginBottom: 12,
    lineHeight: 20,
  },
  cardDetails: {
    marginBottom: 12,
  },
  detailRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 6,
  },
  detailText: {
    fontSize: 14,
    color: colors.textLight,
    marginLeft: 8,
  },
  cardFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  platformText: {
    fontSize: 12,
    color: colors.primary,
    fontWeight: '600',
  },
  emptyContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 64,
  },
  emptyText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: colors.text,
    marginTop: 16,
  },
  emptySubtext: {
    fontSize: 14,
    color: colors.textLight,
    marginTop: 8,
    textAlign: 'center',
  },
});
