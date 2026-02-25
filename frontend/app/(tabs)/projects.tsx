import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
  SafeAreaView,
  Platform,
  ScrollView,
  Share,
} from 'react-native';
import { useRouter } from 'expo-router';
import { BuildingOfficeIcon, MapPinIcon, CurrencyEuroIcon, CalendarIcon, ChevronRightIcon, ShareIcon } from 'react-native-heroicons/outline';
import { colors } from '../../utils/colors';
import api from '../../utils/api';
import { format } from 'date-fns';
import { useTranslation } from 'react-i18next';

interface DeveloperProject {
  id: string;
  developer_name: string;
  project_name: string;
  description: string;
  location: string;
  region?: string;
  budget?: string;
  project_type: string;
  status: string;
  start_date: string;
  expected_completion: string;
  source_url?: string;
  timeline_phases: Array<{
    phase: string;
    status: string;
    progress: number;
  }>;
}

const STATUS_COLORS = {
  planning: colors.info,
  ongoing: colors.success,
  delayed: colors.error,
  completed: colors.textLight,
};

const PHASE_STATUS_COLORS = {
  completed: colors.success,
  ongoing: colors.warning,
  delayed: colors.error,
  pending: colors.textLight,
};

// Region filters
const REGIONS = [
  { id: 'All', label: 'All', flag: '🇩🇪' },
  { id: 'NRW', label: 'NRW', flag: '🏭' },
  { id: 'Brandenburg', label: 'Brandenburg', flag: '🌲' },
];

export default function ProjectsScreen() {
  const [projects, setProjects] = useState<DeveloperProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedRegion, setSelectedRegion] = useState('All');
  const router = useRouter();
  const { t } = useTranslation();

  useEffect(() => {
    fetchProjects();
  }, [selectedRegion]);

  const fetchProjects = async () => {
    try {
      const params = selectedRegion !== 'All' ? { region: selectedRegion } : {};
      const response = await api.get('/developer-projects', { params });
      setProjects(response.data);
    } catch (error) {
      console.error('Failed to fetch projects:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchProjects();
  }, [selectedRegion]);

  const handleRegionChange = (regionId: string) => {
    setSelectedRegion(regionId);
    setLoading(true);
  };

  const shareProject = async (project: DeveloperProject) => {
    try {
      await Share.share({
        message: `${project.project_name}\n\nDeveloper: ${project.developer_name}\nLocation: ${project.location}\nStatus: ${project.status}\n\n${project.description || ''}`,
        title: project.project_name,
      });
    } catch (error) {
      console.error('Error sharing project:', error);
    }
  };

  const renderProjectCard = ({ item }: { item: DeveloperProject }) => (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <View
          style={[
            styles.statusBadge,
            { backgroundColor: STATUS_COLORS[item.status as keyof typeof STATUS_COLORS] || colors.info },
          ]}
        >
          <Text style={styles.statusText}>
            {t(`developerProjects.statuses.${item.status}`) || item.status}
          </Text>
        </View>
        <View style={styles.developerBadge}>
          <BuildingOfficeIcon size={14} color={colors.primary} />
          <Text style={styles.developerText} numberOfLines={1}>
            {item.developer_name.split(' ')[0]}
          </Text>
        </View>
      </View>

      <Text style={styles.cardTitle} numberOfLines={2}>
        {item.project_name}
      </Text>

      <View style={styles.infoRow}>
        <MapPinIcon size={16} color={colors.textLight} />
        <Text style={styles.infoText}>{item.location}</Text>
        {item.region && (
          <View style={styles.regionTag}>
            <Text style={styles.regionTagText}>{item.region}</Text>
          </View>
        )}
      </View>

      {item.budget && (
        <View style={styles.infoRow}>
          <CurrencyEuroIcon size={16} color={colors.textLight} />
          <Text style={styles.infoText}>{item.budget}</Text>
        </View>
      )}

      <Text style={styles.cardDescription} numberOfLines={2}>
        {item.description}
      </Text>

      <View style={styles.timelineSection}>
        <Text style={styles.timelineTitle}>{t('developerProjects.timeline')}</Text>
        {item.timeline_phases && item.timeline_phases.slice(0, 4).map((phase, index) => (
          <View key={index} style={styles.phaseRow}>
            <View
              style={[
                styles.phaseDot,
                { backgroundColor: PHASE_STATUS_COLORS[phase.status as keyof typeof PHASE_STATUS_COLORS] || colors.textLight },
              ]}
            />
            <View style={styles.phaseContent}>
              <Text style={styles.phaseName}>{phase.phase}</Text>
              <View style={styles.progressBar}>
                <View
                  style={[
                    styles.progressFill,
                    {
                      width: `${phase.progress}%`,
                      backgroundColor: PHASE_STATUS_COLORS[phase.status as keyof typeof PHASE_STATUS_COLORS] || colors.textLight,
                    },
                  ]}
                />
              </View>
              <Text style={styles.progressText}>{phase.progress}%</Text>
            </View>
          </View>
        ))}
      </View>

      <View style={styles.cardFooter}>
        <View style={styles.dateInfo}>
          <CalendarIcon size={14} color={colors.textLight} />
          <Text style={styles.dateLabel}>{t('developerProjects.expectedCompletion')}:</Text>
          <Text style={styles.dateValue}>
            {item.expected_completion ? format(new Date(item.expected_completion), 'MMM yyyy') : 'TBD'}
          </Text>
        </View>
        <ChevronRightIcon size={20} color={colors.primary} />
      </View>
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerTop}>
          <Text style={styles.headerTitle}>Developer Projects</Text>
          <Text style={styles.resultsCount}>
            {projects.length} {projects.length === 1 ? 'project' : 'projects'}
          </Text>
        </View>
        
        {/* Region Filters - horizontal scrollable like tender page */}
        <ScrollView 
          horizontal 
          showsHorizontalScrollIndicator={false} 
          style={styles.filtersScroll}
          contentContainerStyle={styles.filtersContainer}
        >
          {REGIONS.map((region) => (
            <TouchableOpacity
              key={region.id}
              style={[
                styles.filterChip,
                selectedRegion === region.id && styles.filterChipActive,
              ]}
              onPress={() => handleRegionChange(region.id)}
            >
              <Text style={styles.filterFlag}>{region.flag}</Text>
              <Text
                style={[
                  styles.filterChipText,
                  selectedRegion === region.id && styles.filterChipTextActive,
                ]}
              >
                {region.label}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      </View>

      {loading ? (
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={colors.primary} />
        </View>
      ) : (
        <FlatList
          data={projects}
          renderItem={renderProjectCard}
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
              <BuildingOfficeIcon size={64} color={colors.textLight} />
              <Text style={styles.emptyText}>{t('developerProjects.noProjects')}</Text>
              <Text style={styles.emptySubtext}>
                No projects found for {selectedRegion === 'All' ? 'any region' : selectedRegion}
              </Text>
            </View>
          }
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  header: {
    backgroundColor: colors.primary,
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 8,
  },
  headerTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#A07D50',  // Exact ochre/gold color matching Tenders page
  },
  resultsCount: {
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.7)',
    fontWeight: '500',
  },
  filtersScroll: {
    flexDirection: 'row',
  },
  filtersContainer: {
    flexDirection: 'row',
    paddingBottom: 4,
  },
  filterChip: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 16,
    marginRight: 8,
    gap: 6,
  },
  filterChipActive: {
    backgroundColor: colors.secondary,
  },
  filterFlag: {
    fontSize: 14,
  },
  filterChipText: {
    fontSize: 13,
    color: 'rgba(255, 255, 255, 0.7)',
    fontWeight: '500',
  },
  filterChipTextActive: {
    color: colors.textWhite,
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
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  statusBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
  },
  statusText: {
    fontSize: 12,
    color: colors.textWhite,
    fontWeight: '600',
    textTransform: 'capitalize',
  },
  developerBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.background,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 12,
    gap: 4,
    maxWidth: 150,
  },
  developerText: {
    fontSize: 11,
    color: colors.primary,
    fontWeight: '600',
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: colors.text,
    marginBottom: 8,
  },
  infoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 6,
    gap: 6,
  },
  infoText: {
    fontSize: 13,
    color: colors.textLight,
    flex: 1,
  },
  regionTag: {
    backgroundColor: colors.secondary,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 8,
  },
  regionTagText: {
    fontSize: 10,
    color: colors.textWhite,
    fontWeight: '600',
  },
  cardDescription: {
    fontSize: 14,
    color: colors.text,
    lineHeight: 20,
    marginTop: 8,
    marginBottom: 12,
  },
  timelineSection: {
    backgroundColor: colors.background,
    padding: 12,
    borderRadius: 12,
    marginBottom: 12,
  },
  timelineTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 12,
  },
  phaseRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 10,
  },
  phaseDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    marginRight: 10,
  },
  phaseContent: {
    flex: 1,
  },
  phaseName: {
    fontSize: 13,
    color: colors.text,
    fontWeight: '500',
    marginBottom: 4,
  },
  progressBar: {
    height: 6,
    backgroundColor: colors.border,
    borderRadius: 3,
    overflow: 'hidden',
    marginBottom: 2,
  },
  progressFill: {
    height: '100%',
  },
  progressText: {
    fontSize: 11,
    color: colors.textLight,
  },
  cardFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  dateInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  dateLabel: {
    fontSize: 12,
    color: colors.textLight,
  },
  dateValue: {
    fontSize: 13,
    color: colors.primary,
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
  emptySubtext: {
    fontSize: 14,
    color: colors.textLight,
    marginTop: 8,
  },
});
