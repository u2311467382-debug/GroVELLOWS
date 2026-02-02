import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  Linking,
} from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
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
  contracting_authority: string;
  participants: string[];
  contact_details: any;
  tender_date: string;
  category: string;
  building_typology?: string;
  platform_source: string;
  platform_url: string;
  status: string;
  is_applied?: boolean;
  application_status?: string;
}

interface Employee {
  id: string;
  name: string;
  email: string;
  role: string;
}

const STATUS_COLORS = {
  'New': colors.success,
  'In Progress': colors.warning,
  'Closed': colors.textLight,
};

export default function TenderDetailScreen() {
  const { id } = useLocalSearchParams();
  const router = useRouter();
  const [tender, setTender] = useState<Tender | null>(null);
  const [loading, setLoading] = useState(true);
  const [isFavorite, setIsFavorite] = useState(false);

  useEffect(() => {
    fetchTenderDetail();
  }, [id]);

  const fetchTenderDetail = async () => {
    try {
      const response = await api.get(`/tenders/${id}`);
      setTender(response.data);
    } catch (error) {
      console.error('Failed to fetch tender:', error);
      Alert.alert('Error', 'Failed to load tender details');
    } finally {
      setLoading(false);
    }
  };

  const toggleFavorite = async () => {
    try {
      if (isFavorite) {
        await api.delete(`/favorites/${id}`);
        setIsFavorite(false);
        Alert.alert('Success', 'Removed from favorites');
      } else {
        await api.post(`/favorites/${id}`);
        setIsFavorite(true);
        Alert.alert('Success', 'Added to favorites');
      }
    } catch (error) {
      console.error('Failed to toggle favorite:', error);
    }
  };

  const updateStatus = async (newStatus: string) => {
    try {
      await api.put(`/tenders/${id}`, { status: newStatus });
      setTender((prev) => prev ? { ...prev, status: newStatus } : null);
      Alert.alert('Success', `Status updated to ${newStatus}`);
    } catch (error) {
      Alert.alert('Error', 'Failed to update status');
    }
  };

  const openPlatformUrl = () => {
    if (tender?.platform_url) {
      Linking.openURL(tender.platform_url);
    }
  };

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  if (!tender) {
    return (
      <View style={styles.centered}>
        <Text style={styles.errorText}>Tender not found</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity
          style={styles.backButton}
          onPress={() => router.back()}
        >
          <Ionicons name="arrow-back" size={24} color={colors.accent} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Tender Details</Text>
        <TouchableOpacity style={styles.favoriteButton} onPress={toggleFavorite}>
          <Ionicons
            name={isFavorite ? 'star' : 'star-outline'}
            size={24}
            color={isFavorite ? colors.warning : colors.accent}
          />
        </TouchableOpacity>
      </View>

      <ScrollView style={styles.content}>
        <View style={styles.topSection}>
          <View style={styles.badges}>
            <View style={styles.statusBadge}>
              <View
                style={[
                  styles.statusDot,
                  { backgroundColor: STATUS_COLORS[tender.status as keyof typeof STATUS_COLORS] },
                ]}
              />
              <Text style={styles.statusText}>{tender.status}</Text>
            </View>
            <View style={styles.categoryBadge}>
              <Text style={styles.categoryText}>{tender.category}</Text>
            </View>
          </View>

          <Text style={styles.title}>{tender.title}</Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Description</Text>
          <Text style={styles.description}>{tender.description}</Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Key Information</Text>
          
          <View style={styles.infoRow}>
            <Ionicons name="cash-outline" size={20} color={colors.primary} />
            <View style={styles.infoContent}>
              <Text style={styles.infoLabel}>Budget</Text>
              <Text style={styles.infoValue}>{tender.budget}</Text>
            </View>
          </View>

          <View style={styles.infoRow}>
            <Ionicons name="calendar-outline" size={20} color={colors.primary} />
            <View style={styles.infoContent}>
              <Text style={styles.infoLabel}>Deadline</Text>
              <Text style={styles.infoValue}>
                {format(new Date(tender.deadline), 'dd MMMM yyyy')}
              </Text>
            </View>
          </View>

          <View style={styles.infoRow}>
            <Ionicons name="time-outline" size={20} color={colors.primary} />
            <View style={styles.infoContent}>
              <Text style={styles.infoLabel}>Tender Date</Text>
              <Text style={styles.infoValue}>
                {format(new Date(tender.tender_date), 'dd MMMM yyyy')}
              </Text>
            </View>
          </View>

          <View style={styles.infoRow}>
            <Ionicons name="location-outline" size={20} color={colors.primary} />
            <View style={styles.infoContent}>
              <Text style={styles.infoLabel}>Location</Text>
              <Text style={styles.infoValue}>{tender.location}</Text>
            </View>
          </View>

          <View style={styles.infoRow}>
            <Ionicons name="briefcase-outline" size={20} color={colors.primary} />
            <View style={styles.infoContent}>
              <Text style={styles.infoLabel}>Project Type</Text>
              <Text style={styles.infoValue}>{tender.project_type}</Text>
            </View>
          </View>

          <View style={styles.infoRow}>
            <Ionicons name="business-outline" size={20} color={colors.primary} />
            <View style={styles.infoContent}>
              <Text style={styles.infoLabel}>Contracting Authority</Text>
              <Text style={styles.infoValue}>{tender.contracting_authority}</Text>
            </View>
          </View>
        </View>

        {tender.participants && tender.participants.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Participants</Text>
            {tender.participants.map((participant, index) => (
              <View key={index} style={styles.participantItem}>
                <Ionicons name="people-outline" size={16} color={colors.primary} />
                <Text style={styles.participantText}>{participant}</Text>
              </View>
            ))}
          </View>
        )}

        {tender.contact_details && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Contact Details</Text>
            {tender.contact_details.name && (
              <View style={styles.contactRow}>
                <Ionicons name="person-outline" size={16} color={colors.primary} />
                <Text style={styles.contactText}>{tender.contact_details.name}</Text>
              </View>
            )}
            {tender.contact_details.email && (
              <View style={styles.contactRow}>
                <Ionicons name="mail-outline" size={16} color={colors.primary} />
                <Text style={styles.contactText}>{tender.contact_details.email}</Text>
              </View>
            )}
            {tender.contact_details.phone && (
              <View style={styles.contactRow}>
                <Ionicons name="call-outline" size={16} color={colors.primary} />
                <Text style={styles.contactText}>{tender.contact_details.phone}</Text>
              </View>
            )}
          </View>
        )}

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Platform</Text>
          <TouchableOpacity
            style={styles.platformButton}
            onPress={openPlatformUrl}
          >
            <Ionicons name="globe-outline" size={20} color={colors.primary} />
            <Text style={styles.platformButtonText}>{tender.platform_source}</Text>
            <Ionicons name="open-outline" size={16} color={colors.primary} />
          </TouchableOpacity>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Update Status</Text>
          <View style={styles.statusButtons}>
            <TouchableOpacity
              style={[
                styles.statusButton,
                tender.status === 'New' && styles.statusButtonActive,
              ]}
              onPress={() => updateStatus('New')}
            >
              <Text
                style={[
                  styles.statusButtonText,
                  tender.status === 'New' && styles.statusButtonTextActive,
                ]}
              >
                New
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[
                styles.statusButton,
                tender.status === 'In Progress' && styles.statusButtonActive,
              ]}
              onPress={() => updateStatus('In Progress')}
            >
              <Text
                style={[
                  styles.statusButtonText,
                  tender.status === 'In Progress' && styles.statusButtonTextActive,
                ]}
              >
                In Progress
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[
                styles.statusButton,
                tender.status === 'Closed' && styles.statusButtonActive,
              ]}
              onPress={() => updateStatus('Closed')}
            >
              <Text
                style={[
                  styles.statusButtonText,
                  tender.status === 'Closed' && styles.statusButtonTextActive,
                ]}
              >
                Closed
              </Text>
            </TouchableOpacity>
          </View>
        </View>
      </ScrollView>
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
  errorText: {
    fontSize: 16,
    color: colors.textLight,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: colors.primary,
    padding: 16,
    paddingTop: 48,
  },
  backButton: {
    padding: 8,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: colors.accent,
  },
  favoriteButton: {
    padding: 8,
  },
  content: {
    flex: 1,
  },
  topSection: {
    backgroundColor: colors.card,
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  badges: {
    flexDirection: 'row',
    marginBottom: 16,
    gap: 8,
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
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: colors.text,
  },
  section: {
    backgroundColor: colors.card,
    padding: 20,
    marginTop: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: colors.text,
    marginBottom: 16,
  },
  description: {
    fontSize: 16,
    color: colors.text,
    lineHeight: 24,
  },
  infoRow: {
    flexDirection: 'row',
    marginBottom: 16,
  },
  infoContent: {
    flex: 1,
    marginLeft: 12,
  },
  infoLabel: {
    fontSize: 12,
    color: colors.textLight,
    marginBottom: 4,
  },
  infoValue: {
    fontSize: 16,
    color: colors.text,
    fontWeight: '500',
  },
  participantItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  participantText: {
    fontSize: 14,
    color: colors.text,
    marginLeft: 8,
  },
  contactRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  contactText: {
    fontSize: 14,
    color: colors.text,
    marginLeft: 8,
  },
  platformButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.background,
    padding: 16,
    borderRadius: 12,
    justifyContent: 'space-between',
  },
  platformButtonText: {
    flex: 1,
    fontSize: 16,
    color: colors.primary,
    fontWeight: '600',
    marginLeft: 12,
  },
  statusButtons: {
    flexDirection: 'row',
    gap: 8,
  },
  statusButton: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 12,
    backgroundColor: colors.background,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
  },
  statusButtonActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  statusButtonText: {
    fontSize: 14,
    color: colors.text,
    fontWeight: '600',
  },
  statusButtonTextActive: {
    color: colors.accent,
  },
});
