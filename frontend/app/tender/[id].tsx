import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  Linking,
  TextInput,
  KeyboardAvoidingView,
  Platform,
  FlatList,
} from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../../utils/colors';
import api from '../../utils/api';
import { format } from 'date-fns';
import { useAuth } from '../../contexts/AuthContext';

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
  direct_link?: string;  // Direct link to the specific tender page
  application_url?: string;
  status: string;
  is_applied?: boolean;
  application_status?: string;
  claimed_by?: string;
  claimed_by_name?: string;
  tender_id?: string;  // Ausschreibungs-ID / Meldungsnummer
}

interface Employee {
  id: string;
  name: string;
  email: string;
  role: string;
}

interface ChatMessage {
  id: string;
  user_id: string;
  user_name: string;
  message: string;
  created_at: string;
}

const STATUS_COLORS = {
  'New': colors.success,
  'In Progress': colors.warning,
  'Closed': colors.textLight,
};

export default function TenderDetailScreen() {
  const { id } = useLocalSearchParams();
  const router = useRouter();
  const { user } = useAuth();
  const [tender, setTender] = useState<Tender | null>(null);
  const [loading, setLoading] = useState(true);
  const [isFavorite, setIsFavorite] = useState(false);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [showShareModal, setShowShareModal] = useState(false);
  const [isApplying, setIsApplying] = useState(false);
  const [isClaiming, setIsClaiming] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [showChat, setShowChat] = useState(false);
  const [sendingMessage, setSendingMessage] = useState(false);
  const [selectedEmployees, setSelectedEmployees] = useState<string[]>([]);
  const chatScrollRef = useRef<ScrollView>(null);

  const canShare = user?.role === 'Director' || user?.role === 'Partner';

  useEffect(() => {
    fetchTenderDetail();
    fetchEmployees();
    fetchChatMessages();
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

  const fetchEmployees = async () => {
    try {
      const response = await api.get('/employees');
      setEmployees(response.data);
    } catch (error) {
      console.error('Failed to fetch employees:', error);
    }
  };

  const fetchChatMessages = async () => {
    try {
      const response = await api.get(`/tenders/${id}/chat`);
      setChatMessages(response.data);
    } catch (error) {
      console.error('Failed to fetch chat:', error);
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

  const handleApply = async () => {
    if (!tender) return;
    try {
      setIsApplying(true);
      if (tender.is_applied) {
        await api.delete(`/tenders/${id}/apply`);
        setTender({ ...tender, is_applied: false, application_status: 'Not Applied' });
        Alert.alert('Success', 'Application removed');
      } else {
        await api.post(`/tenders/${id}/apply`);
        setTender({ ...tender, is_applied: true, application_status: 'Awaiting Results' });
        Alert.alert('Success', 'Application recorded! Status: Awaiting Results');
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to update application');
    } finally {
      setIsApplying(false);
    }
  };

  const handleClaim = async () => {
    if (!tender) return;
    try {
      setIsClaiming(true);
      if (tender.claimed_by) {
        // Already claimed - unclaim only if it's the same user
        if (tender.claimed_by === user?.id) {
          await api.delete(`/tenders/${id}/claim`);
          setTender({ ...tender, claimed_by: undefined, claimed_by_name: undefined });
          Alert.alert('Success', 'You have released this tender');
        } else {
          Alert.alert('Info', `This tender is being handled by ${tender.claimed_by_name}`);
        }
      } else {
        await api.post(`/tenders/${id}/claim`);
        setTender({ ...tender, claimed_by: user?.id, claimed_by_name: user?.name });
        Alert.alert('Success', 'You are now working on this tender');
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to update claim status');
    } finally {
      setIsClaiming(false);
    }
  };

  const toggleEmployeeSelection = (empId: string) => {
    setSelectedEmployees(prev => 
      prev.includes(empId) 
        ? prev.filter(id => id !== empId)
        : [...prev, empId]
    );
  };

  const handleShareToSelected = async () => {
    if (selectedEmployees.length === 0) {
      Alert.alert('Select Employees', 'Please select at least one team member to share with');
      return;
    }
    try {
      await api.post('/share/tender', {
        tender_id: id,
        recipient_ids: selectedEmployees,
        message: `Tender shared: ${tender?.title}`
      });
      Alert.alert('Shared!', `Tender shared with ${selectedEmployees.length} team member(s)`);
      setShowShareModal(false);
      setSelectedEmployees([]);
    } catch (error) {
      Alert.alert('Error', 'Failed to share tender');
    }
  };

  const handleSendMessage = async () => {
    if (!newMessage.trim()) return;
    try {
      setSendingMessage(true);
      await api.post(`/tenders/${id}/chat`, { message: newMessage.trim() });
      setNewMessage('');
      fetchChatMessages();
      setTimeout(() => chatScrollRef.current?.scrollToEnd({ animated: true }), 100);
    } catch (error) {
      Alert.alert('Error', 'Failed to send message');
    } finally {
      setSendingMessage(false);
    }
  };

  const handleShare = async (recipientId: string, recipientName: string) => {
    try {
      await api.post('/share/tender', {
        tender_id: id,
        recipient_ids: [recipientId],
        message: `Check out this tender: ${tender?.title}`
      });
      Alert.alert('Shared!', `Tender shared with ${recipientName}`);
      setShowShareModal(false);
    } catch (error) {
      Alert.alert('Error', 'Failed to share tender');
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
    // Prioritize direct_link (specific tender page), fallback to platform_url
    const url = tender?.direct_link || tender?.platform_url;
    if (url) {
      Linking.openURL(url);
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
            {tender.building_typology && (
              <View style={styles.typologyBadge}>
                <Text style={styles.typologyText}>{tender.building_typology}</Text>
              </View>
            )}
          </View>

          {tender.is_applied && (
            <View style={styles.applicationStatus}>
              <Ionicons name="checkmark-circle" size={16} color={colors.success} />
              <Text style={styles.applicationStatusText}>
                Applied - {tender.application_status}
              </Text>
            </View>
          )}

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

        {/* Links Section - Platform & Application */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Links</Text>
          
          {/* View Tender on Platform */}
          <TouchableOpacity
            style={styles.linkButton}
            onPress={openPlatformUrl}
          >
            <View style={styles.linkIconContainer}>
              <Ionicons name="globe-outline" size={20} color={colors.primary} />
            </View>
            <View style={styles.linkContent}>
              <Text style={styles.linkLabel}>
                {tender.direct_link ? 'View Tender Details' : 'View on Portal'}
              </Text>
              <Text style={styles.linkSource} numberOfLines={1}>
                {tender.direct_link ? `Direct link on ${tender.platform_source}` : tender.platform_source}
              </Text>
            </View>
            <Ionicons name="open-outline" size={18} color={colors.primary} />
          </TouchableOpacity>

          {/* Info banner about direct link */}
          {tender.direct_link && (
            <View style={styles.infoBanner}>
              <Ionicons name="checkmark-circle" size={18} color={colors.success} />
              <Text style={styles.infoText}>
                Direct link available - opens the specific tender page on {tender.platform_source}
              </Text>
            </View>
          )}

          {/* Warning if no direct link */}
          {!tender.direct_link && (
            <View style={styles.warningBanner}>
              <Ionicons name="information-circle" size={18} color="#F57C00" />
              <Text style={styles.warningText}>
                No direct link available. You may need to search for this tender on the portal.
              </Text>
            </View>
          )}
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

        {/* Action Buttons */}
        <View style={styles.actionSection}>
          <TouchableOpacity 
            style={[styles.actionButton, tender.is_applied && styles.actionButtonApplied]}
            onPress={handleApply}
            disabled={isApplying}
          >
            {isApplying ? (
              <ActivityIndicator size="small" color={colors.textWhite} />
            ) : (
              <>
                <Ionicons 
                  name={tender.is_applied ? "checkmark-circle" : "send"} 
                  size={20} 
                  color={colors.textWhite} 
                />
                <Text style={styles.actionButtonText}>
                  {tender.is_applied ? 'Applied' : 'Apply to Tender'}
                </Text>
              </>
            )}
          </TouchableOpacity>

          <TouchableOpacity 
            style={styles.shareButton}
            onPress={() => setShowShareModal(true)}
          >
            <Ionicons name="share-social" size={20} color={colors.primary} />
            <Text style={styles.shareButtonText}>Share with Team</Text>
          </TouchableOpacity>
        </View>

        {/* Employee List for Sharing */}
        {showShareModal && (
          <View style={styles.shareModal}>
            <View style={styles.shareModalHeader}>
              <Text style={styles.shareModalTitle}>Share with Team Member</Text>
              <TouchableOpacity onPress={() => setShowShareModal(false)}>
                <Ionicons name="close" size={24} color={colors.textDark} />
              </TouchableOpacity>
            </View>
            {employees.map((emp) => (
              <TouchableOpacity 
                key={emp.id}
                style={styles.employeeItem}
                onPress={() => handleShare(emp.id, emp.name)}
              >
                <View style={styles.employeeAvatar}>
                  <Text style={styles.employeeAvatarText}>
                    {emp.name.split(' ').map(n => n[0]).join('')}
                  </Text>
                </View>
                <View style={styles.employeeInfo}>
                  <Text style={styles.employeeName}>{emp.name}</Text>
                  <Text style={styles.employeeRole}>{emp.role}</Text>
                </View>
                <Ionicons name="arrow-forward" size={20} color={colors.textLight} />
              </TouchableOpacity>
            ))}
          </View>
        )}
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
  linkButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.background,
    padding: 14,
    borderRadius: 12,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: colors.border,
  },
  applicationLinkButton: {
    backgroundColor: '#FFF8E1',
    borderColor: colors.secondary,
    borderWidth: 2,
  },
  linkIconContainer: {
    width: 40,
    height: 40,
    borderRadius: 10,
    backgroundColor: colors.primaryLight,
    justifyContent: 'center',
    alignItems: 'center',
  },
  applicationIconContainer: {
    backgroundColor: colors.secondary,
  },
  linkContent: {
    flex: 1,
    marginLeft: 12,
  },
  linkLabel: {
    fontSize: 15,
    fontWeight: '600',
    color: colors.text,
  },
  applicationLabel: {
    color: colors.secondary,
  },
  linkSource: {
    fontSize: 13,
    color: colors.textLight,
    marginTop: 2,
  },
  linkSubtext: {
    fontSize: 12,
    color: colors.textLight,
    marginTop: 2,
  },
  warningBanner: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    backgroundColor: '#FFF3E0',
    padding: 12,
    borderRadius: 8,
    borderLeftWidth: 3,
    borderLeftColor: '#F57C00',
    gap: 8,
  },
  warningText: {
    flex: 1,
    fontSize: 13,
    color: '#E65100',
    lineHeight: 18,
  },
  infoBanner: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    backgroundColor: '#E8F5E9',
    padding: 12,
    borderRadius: 8,
    borderLeftWidth: 3,
    borderLeftColor: colors.success,
    gap: 8,
    marginBottom: 12,
  },
  infoText: {
    flex: 1,
    fontSize: 13,
    color: '#2E7D32',
    lineHeight: 18,
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
  typologyBadge: {
    backgroundColor: '#E8F5E9',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 10,
  },
  typologyText: {
    fontSize: 12,
    color: '#2E7D32',
    fontWeight: '600',
  },
  applicationStatus: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#E8F5E9',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    marginTop: 12,
    gap: 6,
  },
  applicationStatusText: {
    fontSize: 14,
    color: '#2E7D32',
    fontWeight: '600',
  },
  actionSection: {
    padding: 20,
    gap: 12,
  },
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.secondary,
    paddingVertical: 16,
    borderRadius: 12,
    gap: 8,
  },
  actionButtonApplied: {
    backgroundColor: colors.success,
  },
  actionButtonText: {
    fontSize: 16,
    color: colors.textWhite,
    fontWeight: '600',
  },
  shareButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.background,
    paddingVertical: 16,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: colors.primary,
    gap: 8,
  },
  shareButtonText: {
    fontSize: 16,
    color: colors.primary,
    fontWeight: '600',
  },
  shareModal: {
    backgroundColor: colors.card,
    padding: 20,
    marginTop: 16,
    borderRadius: 12,
  },
  shareModalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  shareModalTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: colors.text,
  },
  employeeItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  employeeAvatar: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.primary,
    justifyContent: 'center',
    alignItems: 'center',
  },
  employeeAvatarText: {
    color: colors.textWhite,
    fontWeight: '600',
    fontSize: 14,
  },
  employeeInfo: {
    flex: 1,
    marginLeft: 12,
  },
  employeeName: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.text,
  },
  employeeRole: {
    fontSize: 14,
    color: colors.textLight,
  },
});
