import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Alert,
  Switch,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../../utils/colors';
import { useAuth } from '../../contexts/AuthContext';
import api from '../../utils/api';
import { useTranslation } from 'react-i18next';
import { changeLanguage } from '../../utils/i18n';

export default function ProfileScreen() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const [linkedinUrl, setLinkedinUrl] = useState(user?.linkedin_url || '');
  const [notifications, setNotifications] = useState(
    user?.notification_preferences || {
      new_tenders: true,
      status_changes: true,
      ipa_tenders: true,
      project_management: true,
      daily_digest: true,
    }
  );

  const handleUpdateLinkedIn = async () => {
    try {
      await api.put('/auth/linkedin', null, {
        params: { linkedin_url: linkedinUrl },
      });
      Alert.alert('Success', 'LinkedIn URL updated');
    } catch (error) {
      Alert.alert('Error', 'Failed to update LinkedIn URL');
    }
  };

  const handleUpdateNotifications = async () => {
    try {
      await api.put('/auth/preferences', notifications);
      Alert.alert('Success', 'Notification preferences updated');
    } catch (error) {
      Alert.alert('Error', 'Failed to update preferences');
    }
  };

  const handleLogout = () => {
    Alert.alert('Logout', 'Are you sure you want to logout?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Logout',
        style: 'destructive',
        onPress: async () => {
          await logout();
          router.replace('/(auth)/login');
        },
      },
    ]);
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <View style={styles.avatarContainer}>
          <Ionicons name="person" size={48} color={colors.accent} />
        </View>
        <Text style={styles.name}>{user?.name}</Text>
        <Text style={styles.email}>{user?.email}</Text>
        <View style={styles.roleBadge}>
          <Text style={styles.roleText}>{user?.role}</Text>
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>LinkedIn Profile</Text>
        <View style={styles.inputContainer}>
          <TextInput
            style={styles.input}
            placeholder="LinkedIn Profile URL"
            value={linkedinUrl}
            onChangeText={setLinkedinUrl}
            placeholderTextColor={colors.textLight}
          />
        </View>
        <TouchableOpacity
          style={styles.saveButton}
          onPress={handleUpdateLinkedIn}
        >
          <Text style={styles.saveButtonText}>Save LinkedIn URL</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Notification Preferences</Text>
        
        <View style={styles.settingRow}>
          <View style={styles.settingInfo}>
            <Ionicons name="notifications-outline" size={20} color={colors.primary} />
            <Text style={styles.settingText}>New Tenders</Text>
          </View>
          <Switch
            value={notifications.new_tenders}
            onValueChange={(value) =>
              setNotifications({ ...notifications, new_tenders: value })
            }
            trackColor={{ false: colors.border, true: colors.primaryLight }}
            thumbColor={notifications.new_tenders ? colors.primary : colors.textLight}
          />
        </View>

        <View style={styles.settingRow}>
          <View style={styles.settingInfo}>
            <Ionicons name="sync-outline" size={20} color={colors.primary} />
            <Text style={styles.settingText}>Status Changes</Text>
          </View>
          <Switch
            value={notifications.status_changes}
            onValueChange={(value) =>
              setNotifications({ ...notifications, status_changes: value })
            }
            trackColor={{ false: colors.border, true: colors.primaryLight }}
            thumbColor={notifications.status_changes ? colors.primary : colors.textLight}
          />
        </View>

        <View style={styles.settingRow}>
          <View style={styles.settingInfo}>
            <Ionicons name="flag-outline" size={20} color={colors.primary} />
            <Text style={styles.settingText}>IPA Tenders</Text>
          </View>
          <Switch
            value={notifications.ipa_tenders}
            onValueChange={(value) =>
              setNotifications({ ...notifications, ipa_tenders: value })
            }
            trackColor={{ false: colors.border, true: colors.primaryLight }}
            thumbColor={notifications.ipa_tenders ? colors.primary : colors.textLight}
          />
        </View>

        <View style={styles.settingRow}>
          <View style={styles.settingInfo}>
            <Ionicons name="construct-outline" size={20} color={colors.primary} />
            <Text style={styles.settingText}>Project Management</Text>
          </View>
          <Switch
            value={notifications.project_management}
            onValueChange={(value) =>
              setNotifications({ ...notifications, project_management: value })
            }
            trackColor={{ false: colors.border, true: colors.primaryLight }}
            thumbColor={notifications.project_management ? colors.primary : colors.textLight}
          />
        </View>

        <View style={styles.settingRow}>
          <View style={styles.settingInfo}>
            <Ionicons name="mail-outline" size={20} color={colors.primary} />
            <Text style={styles.settingText}>Daily Digest</Text>
          </View>
          <Switch
            value={notifications.daily_digest}
            onValueChange={(value) =>
              setNotifications({ ...notifications, daily_digest: value })
            }
            trackColor={{ false: colors.border, true: colors.primaryLight }}
            thumbColor={notifications.daily_digest ? colors.primary : colors.textLight}
          />
        </View>

        <TouchableOpacity
          style={styles.saveButton}
          onPress={handleUpdateNotifications}
        >
          <Text style={styles.saveButtonText}>Save Preferences</Text>
        </TouchableOpacity>
      </View>

      <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
        <Ionicons name="log-out-outline" size={20} color={colors.error} />
        <Text style={styles.logoutText}>Logout</Text>
      </TouchableOpacity>

      <View style={styles.footer}>
        <Text style={styles.footerText}>GroVELLOWS v1.0</Text>
        <Text style={styles.footerText}>German Construction Tenders</Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  header: {
    backgroundColor: colors.primary,
    padding: 32,
    alignItems: 'center',
  },
  avatarContainer: {
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: colors.primaryLight,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  name: {
    fontSize: 24,
    fontWeight: 'bold',
    color: colors.accent,
    marginBottom: 4,
  },
  email: {
    fontSize: 16,
    color: colors.textLight,
    marginBottom: 12,
  },
  roleBadge: {
    backgroundColor: colors.secondary,
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 16,
  },
  roleText: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.card,
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
  inputContainer: {
    backgroundColor: colors.background,
    borderRadius: 12,
    marginBottom: 16,
  },
  input: {
    height: 48,
    paddingHorizontal: 16,
    fontSize: 16,
    color: colors.text,
  },
  saveButton: {
    backgroundColor: colors.primary,
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
  },
  saveButtonText: {
    color: colors.accent,
    fontSize: 16,
    fontWeight: '600',
  },
  settingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  settingInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  settingText: {
    fontSize: 16,
    color: colors.text,
    marginLeft: 12,
  },
  logoutButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.card,
    marginTop: 16,
    marginHorizontal: 20,
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.error,
  },
  logoutText: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.error,
    marginLeft: 8,
  },
  footer: {
    alignItems: 'center',
    padding: 32,
  },
  footerText: {
    fontSize: 12,
    color: colors.textLight,
    marginBottom: 4,
  },
});
