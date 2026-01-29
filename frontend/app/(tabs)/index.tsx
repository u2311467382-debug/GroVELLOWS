import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  TextInput,
  ActivityIndicator,
  RefreshControl,
  Modal,
  ScrollView,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../../utils/colors';
import api from '../../utils/api';
import { format } from 'date-fns';
import { useTranslation } from 'react-i18next';

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
  building_typology?: string;
  is_applied?: boolean;
  application_status?: string;
}

const STATUS_COLORS = {
  'New': colors.success,
  'In Progress': colors.warning,
  'Closed': colors.textLight,
};

const APPLICATION_STATUS_COLORS = {
  'Not Applied': colors.textLight,
  'Awaiting Results': colors.warning,
  'Won': colors.success,
  'Lost': colors.error,
};

const CATEGORIES = [
  'All', 'IPA', 'IPD', 'Integrated Project Management', 'Project Management',
  'Risk Management', 'Lean Management', 'Procurement Management',
  'Organization Alignment Workshops', 'Construction Supervision',
  'Change Order Management', 'Cost Management', 'Tendering Process',
  'Project Completion', 'Handover Documentation', 'General'
];

const BUILDING_TYPOLOGIES = [
  'All', 'Residential', 'Commercial', 'Mixed-Use', 'Healthcare', 
  'Data Center', 'Infrastructure', 'Industrial'
];

const STATUSES = ['All', 'New', 'In Progress', 'Closed'];
const SORT_OPTIONS = [
  { label: 'Newest First', value: 'date_desc' },
  { label: 'Deadline Soon', value: 'deadline_asc' },
  { label: 'Budget High-Low', value: 'budget_desc' },
  { label: 'Budget Low-High', value: 'budget_asc' },
];

export default function TendersScreen() {
  const [tenders, setTenders] = useState<Tender[]>([]);
  const [filteredTenders, setFilteredTenders] = useState<Tender[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [selectedStatus, setSelectedStatus] = useState('All');
  const [selectedTypology, setSelectedTypology] = useState('All');
  const [sortBy, setSortBy] = useState('date_desc');
  const [showFilters, setShowFilters] = useState(false);
  const [viewMode, setViewMode] = useState<'list' | 'compact'>('list');
  const [applyingId, setApplyingId] = useState<string | null>(null);
  const router = useRouter();
  const { t } = useTranslation();

  useEffect(() => {
    fetchTenders();
  }, []);

  useEffect(() => {
    filterAndSortTenders();
  }, [tenders, searchQuery, selectedCategory, selectedStatus, selectedTypology, sortBy]);

  const fetchTenders = async () => {
    try {
      const response = await api.get('/tenders');
      setTenders(response.data);
    } catch (error) {
      console.error('Failed to fetch tenders:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchTenders();
  }, []);

  const filterAndSortTenders = () => {
    let filtered = [...tenders];

    // Search filter
    if (searchQuery) {
      filtered = filtered.filter(
        (tender) =>
          tender.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
          tender.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
          tender.location.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    // Category filter
    if (selectedCategory !== 'All') {
      filtered = filtered.filter((tender) => tender.category === selectedCategory);
    }

    // Status filter
    if (selectedStatus !== 'All') {
      filtered = filtered.filter((tender) => tender.status === selectedStatus);
    }

    // Sorting
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'deadline_asc':
          return new Date(a.deadline).getTime() - new Date(b.deadline).getTime();
        case 'budget_desc':
          return parseBudget(b.budget) - parseBudget(a.budget);
        case 'budget_asc':
          return parseBudget(a.budget) - parseBudget(b.budget);
        default: // date_desc
          return new Date(b.deadline).getTime() - new Date(a.deadline).getTime();
      }
    });

    setFilteredTenders(filtered);
  };

  const parseBudget = (budget: string): number => {
    const match = budget.match(/[\d,]+/);
    if (match) {
      return parseInt(match[0].replace(/,/g, ''));
    }
    return 0;
  };

  const clearFilters = () => {
    setSelectedCategory('All');
    setSelectedStatus('All');
    setSearchQuery('');
    setSortBy('date_desc');
  };

  const renderCompactCard = ({ item }: { item: Tender }) => (
    <TouchableOpacity
      style={styles.compactCard}
      onPress={() => router.push(`/tender/${item.id}`)}
    >
      <View style={styles.compactHeader}>
        <View style={[styles.compactStatusDot, { backgroundColor: STATUS_COLORS[item.status as keyof typeof STATUS_COLORS] }]} />
        <Text style={styles.compactTitle} numberOfLines={1}>{item.title}</Text>
      </View>
      <View style={styles.compactInfo}>
        <Text style={styles.compactBudget}>{item.budget}</Text>
        <Text style={styles.compactDeadline}>Due: {format(new Date(item.deadline), 'dd MMM')}</Text>
      </View>
    </TouchableOpacity>
  );

  const renderTenderCard = ({ item }: { item: Tender }) => (
    <TouchableOpacity
      style={styles.card}
      onPress={() => router.push(`/tender/${item.id}`)}
      activeOpacity={0.7}
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
          <Text style={styles.categoryText} numberOfLines={1}>{item.category}</Text>
        </View>
      </View>

      <Text style={styles.cardTitle} numberOfLines={2}>
        {item.title}
      </Text>

      <View style={styles.cardDetails}>
        <View style={styles.detailRow}>
          <Ionicons name="location" size={14} color={colors.textLight} />
          <Text style={styles.detailText} numberOfLines={1}>{item.location}</Text>
        </View>
        <View style={styles.detailRow}>
          <Ionicons name="cash" size={14} color={colors.secondary} />
          <Text style={[styles.detailText, styles.budgetText]}>{item.budget}</Text>
        </View>
        <View style={styles.detailRow}>
          <Ionicons name="calendar" size={14} color={colors.error} />
          <Text style={styles.detailText}>
            {format(new Date(item.deadline), 'dd MMM yyyy')}
          </Text>
        </View>
      </View>

      <View style={styles.cardFooter}>
        <Text style={styles.platformText} numberOfLines={1}>{item.platform_source}</Text>
        <Ionicons name="arrow-forward" size={16} color={colors.primary} />
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
      {/* Enhanced Header */}
      <View style={styles.header}>
        <View style={styles.searchRow}>
          <View style={styles.searchContainer}>
            <Ionicons name="search" size={18} color={colors.textLight} />
            <TextInput
              style={styles.searchInput}
              placeholder={t('tenders.search')}
              value={searchQuery}
              onChangeText={setSearchQuery}
              placeholderTextColor={colors.textLight}
            />
            {searchQuery ? (
              <TouchableOpacity onPress={() => setSearchQuery('')}>
                <Ionicons name="close-circle" size={18} color={colors.textLight} />
              </TouchableOpacity>
            ) : null}
          </View>
          <TouchableOpacity
            style={styles.iconButton}
            onPress={() => setShowFilters(true)}
          >
            <Ionicons name="options" size={22} color={colors.primary} />
            {(selectedCategory !== 'All' || selectedStatus !== 'All') && (
              <View style={styles.filterDot} />
            )}
          </TouchableOpacity>
        </View>

        {/* Quick Filters */}
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.quickFilters}>
          <TouchableOpacity
            style={[styles.quickFilterChip, sortBy !== 'date_desc' && styles.quickFilterChipActive]}
            onPress={() => setSortBy(sortBy === 'date_desc' ? 'deadline_asc' : 'date_desc')}
          >
            <Ionicons name="swap-vertical" size={14} color={sortBy !== 'date_desc' ? colors.textWhite : colors.primary} />
            <Text style={[styles.quickFilterText, sortBy !== 'date_desc' && styles.quickFilterTextActive]}>Sort</Text>
          </TouchableOpacity>
          
          <TouchableOpacity
            style={[styles.quickFilterChip, selectedStatus !== 'All' && styles.quickFilterChipActive]}
            onPress={() => setSelectedStatus(selectedStatus === 'All' ? 'New' : 'All')}
          >
            <Text style={[styles.quickFilterText, selectedStatus !== 'All' && styles.quickFilterTextActive]}>New Only</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.quickFilterChip, viewMode === 'compact' && styles.quickFilterChipActive]}
            onPress={() => setViewMode(viewMode === 'list' ? 'compact' : 'list')}
          >
            <Ionicons 
              name={viewMode === 'list' ? 'list' : 'grid'} 
              size={14} 
              color={viewMode === 'compact' ? colors.textWhite : colors.primary} 
            />
            <Text style={[styles.quickFilterText, viewMode === 'compact' && styles.quickFilterTextActive]}>View</Text>
          </TouchableOpacity>

          {(selectedCategory !== 'All' || selectedStatus !== 'All' || searchQuery) && (
            <TouchableOpacity style={styles.clearButton} onPress={clearFilters}>
              <Ionicons name="close" size={14} color={colors.error} />
              <Text style={styles.clearButtonText}>Clear</Text>
            </TouchableOpacity>
          )}
        </ScrollView>

        {/* Results Count */}
        <Text style={styles.resultsCount}>
          {filteredTenders.length} {filteredTenders.length === 1 ? 'tender' : 'tenders'} found
        </Text>
      </View>

      <FlatList
        data={filteredTenders}
        renderItem={viewMode === 'compact' ? renderCompactCard : renderTenderCard}
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
            <Ionicons name="document-outline" size={64} color={colors.textLight} />
            <Text style={styles.emptyText}>{t('tenders.noTenders')}</Text>
            <TouchableOpacity style={styles.emptyButton} onPress={clearFilters}>
              <Text style={styles.emptyButtonText}>Clear Filters</Text>
            </TouchableOpacity>
          </View>
        }
      />

      {/* Enhanced Filter Modal */}
      <Modal
        visible={showFilters}
        animationType="slide"
        transparent={true}
        onRequestClose={() => setShowFilters(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Filters & Sorting</Text>
              <TouchableOpacity onPress={() => setShowFilters(false)}>
                <Ionicons name="close" size={26} color={colors.text} />
              </TouchableOpacity>
            </View>

            <ScrollView style={styles.modalBody} showsVerticalScrollIndicator={false}>
              {/* Sort Section */}
              <View style={styles.filterSection}>
                <Text style={styles.filterLabel}>Sort By</Text>
                {SORT_OPTIONS.map((option) => (
                  <TouchableOpacity
                    key={option.value}
                    style={[
                      styles.filterOptionRow,
                      sortBy === option.value && styles.filterOptionRowActive,
                    ]}
                    onPress={() => setSortBy(option.value)}
                  >
                    <Text
                      style={[
                        styles.filterOptionRowText,
                        sortBy === option.value && styles.filterOptionRowTextActive,
                      ]}
                    >
                      {option.label}
                    </Text>
                    {sortBy === option.value && (
                      <Ionicons name="checkmark" size={20} color={colors.secondary} />
                    )}
                  </TouchableOpacity>
                ))}
              </View>

              {/* Category Section */}
              <View style={styles.filterSection}>
                <Text style={styles.filterLabel}>Category</Text>
                <View style={styles.filterGrid}>
                  {CATEGORIES.map((cat) => (
                    <TouchableOpacity
                      key={cat}
                      style={[
                        styles.filterChip,
                        selectedCategory === cat && styles.filterChipActive,
                      ]}
                      onPress={() => setSelectedCategory(cat)}
                    >
                      <Text
                        style={[
                          styles.filterChipText,
                          selectedCategory === cat && styles.filterChipTextActive,
                        ]}
                      >
                        {cat}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>
              </View>

              {/* Status Section */}
              <View style={styles.filterSection}>
                <Text style={styles.filterLabel}>Status</Text>
                <View style={styles.filterGrid}>
                  {STATUSES.map((status) => (
                    <TouchableOpacity
                      key={status}
                      style={[
                        styles.filterChip,
                        selectedStatus === status && styles.filterChipActive,
                      ]}
                      onPress={() => setSelectedStatus(status)}
                    >
                      <Text
                        style={[
                          styles.filterChipText,
                          selectedStatus === status && styles.filterChipTextActive,
                        ]}
                      >
                        {status}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>
              </View>
            </ScrollView>

            <View style={styles.modalFooter}>
              <TouchableOpacity style={styles.secondaryButton} onPress={clearFilters}>
                <Ionicons name="refresh" size={18} color={colors.primary} />
                <Text style={styles.secondaryButtonText}>Reset All</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.primaryButton}
                onPress={() => setShowFilters(false)}
              >
                <Text style={styles.primaryButtonText}>Apply ({filteredTenders.length})</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
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
  header: {
    backgroundColor: colors.card,
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  searchRow: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 12,
  },
  searchContainer: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.background,
    borderRadius: 12,
    paddingHorizontal: 12,
    height: 44,
    gap: 8,
  },
  searchInput: {
    flex: 1,
    fontSize: 15,
    color: colors.text,
  },
  iconButton: {
    width: 44,
    height: 44,
    borderRadius: 12,
    backgroundColor: colors.background,
    justifyContent: 'center',
    alignItems: 'center',
    position: 'relative',
  },
  filterDot: {
    position: 'absolute',
    top: 8,
    right: 8,
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.secondary,
  },
  quickFilters: {
    marginBottom: 8,
  },
  quickFilterChip: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.background,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    marginRight: 8,
    gap: 4,
    borderWidth: 1,
    borderColor: colors.border,
  },
  quickFilterChipActive: {
    backgroundColor: colors.secondary,
    borderColor: colors.secondary,
  },
  quickFilterText: {
    fontSize: 13,
    color: colors.primary,
    fontWeight: '500',
  },
  quickFilterTextActive: {
    color: colors.textWhite,
  },
  clearButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.background,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    marginRight: 8,
    gap: 4,
    borderWidth: 1,
    borderColor: colors.error,
  },
  clearButtonText: {
    fontSize: 13,
    color: colors.error,
    fontWeight: '500',
  },
  resultsCount: {
    fontSize: 12,
    color: colors.textLight,
    marginTop: 4,
  },
  list: {
    padding: 16,
  },
  card: {
    backgroundColor: colors.card,
    borderRadius: 12,
    padding: 14,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08,
    shadowRadius: 3,
    elevation: 2,
  },
  compactCard: {
    backgroundColor: colors.card,
    borderRadius: 10,
    padding: 12,
    marginBottom: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },
  compactHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 6,
    gap: 8,
  },
  compactStatusDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  compactTitle: {
    flex: 1,
    fontSize: 14,
    fontWeight: '600',
    color: colors.text,
  },
  compactInfo: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  compactBudget: {
    fontSize: 13,
    color: colors.secondary,
    fontWeight: '600',
  },
  compactDeadline: {
    fontSize: 12,
    color: colors.textLight,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 10,
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.background,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 10,
  },
  statusDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    marginRight: 5,
  },
  statusText: {
    fontSize: 11,
    color: colors.text,
    fontWeight: '600',
  },
  categoryBadge: {
    backgroundColor: colors.primaryLight,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 10,
    maxWidth: 180,
  },
  categoryText: {
    fontSize: 11,
    color: colors.secondary,
    fontWeight: '600',
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: colors.text,
    marginBottom: 10,
    lineHeight: 22,
  },
  cardDetails: {
    marginBottom: 10,
  },
  detailRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 5,
    gap: 6,
  },
  detailText: {
    fontSize: 13,
    color: colors.textLight,
    flex: 1,
  },
  budgetText: {
    color: colors.secondary,
    fontWeight: '600',
  },
  cardFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  platformText: {
    fontSize: 11,
    color: colors.primary,
    fontWeight: '500',
    flex: 1,
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
    marginBottom: 16,
  },
  emptyButton: {
    paddingHorizontal: 24,
    paddingVertical: 10,
    backgroundColor: colors.primary,
    borderRadius: 20,
  },
  emptyButtonText: {
    color: colors.textWhite,
    fontWeight: '600',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: colors.card,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    maxHeight: '85%',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: colors.text,
  },
  modalBody: {
    padding: 20,
  },
  filterSection: {
    marginBottom: 24,
  },
  filterLabel: {
    fontSize: 15,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 12,
  },
  filterGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  filterChip: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 16,
    backgroundColor: colors.background,
    borderWidth: 1,
    borderColor: colors.border,
  },
  filterChipActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  filterChipText: {
    fontSize: 13,
    color: colors.text,
    fontWeight: '500',
  },
  filterChipTextActive: {
    color: colors.textWhite,
    fontWeight: '600',
  },
  filterOptionRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 16,
    backgroundColor: colors.background,
    borderRadius: 10,
    marginBottom: 8,
  },
  filterOptionRowActive: {
    backgroundColor: colors.primaryLight,
  },
  filterOptionRowText: {
    fontSize: 14,
    color: colors.text,
    fontWeight: '500',
  },
  filterOptionRowTextActive: {
    color: colors.secondary,
    fontWeight: '600',
  },
  modalFooter: {
    flexDirection: 'row',
    padding: 20,
    gap: 12,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  secondaryButton: {
    flex: 1,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 14,
    borderRadius: 12,
    backgroundColor: colors.background,
    gap: 6,
  },
  secondaryButtonText: {
    fontSize: 15,
    fontWeight: '600',
    color: colors.primary,
  },
  primaryButton: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: 12,
    backgroundColor: colors.secondary,
    alignItems: 'center',
  },
  primaryButtonText: {
    fontSize: 15,
    fontWeight: '600',
    color: colors.textWhite,
  },
});