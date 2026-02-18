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
}

const STATUS_COLORS = {
  'New': colors.success,
  'In Progress': colors.warning,
  'Closed': colors.textLight,
};

export default function FavoritesScreen() {
  const [favorites, setFavorites] = useState<Tender[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const router = useRouter();

  useEffect(() => {
    fetchFavorites();
  }, []);

  const fetchFavorites = async () => {
    try {
      const response = await api.get('/favorites');
      setFavorites(response.data);
    } catch (error) {
      console.error('Failed to fetch favorites:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchFavorites();
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
              { backgroundColor: STATUS_COLORS[item.status as keyof typeof STATUS_COLORS] },
            ]}
          />
          <Text style={styles.statusText}>{item.status}</Text>
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
            {format(new Date(item.deadline), 'dd MMM yyyy')}
          </Text>
        </View>
      </View>

      <View style={styles.cardFooter}>
        <Text style={styles.platformText}>{item.platform_source}</Text>
        <Ionicons name="chevron-forward" size={20} color={colors.primary} />
      </View>
    </TouchableOpacity>
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
  },
});
