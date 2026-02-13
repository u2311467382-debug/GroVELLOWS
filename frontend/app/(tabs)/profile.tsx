import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Alert,
  Switch,
  Modal,
  Image,
  ActivityIndicator,
} from 'react-native';
import { useRouter } from 'expo-router';
import { ShieldCheckIcon, KeyIcon, UserIcon, GlobeAltIcon, BellIcon, ArrowRightOnRectangleIcon, DevicePhoneMobileIcon, QrCodeIcon } from 'react-native-heroicons/outline';
import { colors } from '../../utils/colors';
import { useAuth } from '../../contexts/AuthContext';
import api from '../../utils/api';
import { useTranslation } from 'react-i18next';
import { changeLanguage } from '../../utils/i18n';

export default function ProfileScreen() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const { t, i18n } = useTranslation();
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
  
  // MFA State
  const [mfaEnabled, setMfaEnabled] = useState(false);
  const [mfaLoading, setMfaLoading] = useState(false);
  const [showMfaSetup, setShowMfaSetup] = useState(false);
  const [mfaQrCode, setMfaQrCode] = useState('');
  const [mfaSecret, setMfaSecret] = useState('');
  const [mfaCode, setMfaCode] = useState('');
  const [backupCodes, setBackupCodes] = useState<string[]>([]);
  const [showBackupCodes, setShowBackupCodes] = useState(false);
  const [password, setPassword] = useState('');
  const [backupCodesRemaining, setBackupCodesRemaining] = useState(0);

  useEffect(() => {
    fetchMfaStatus();
  }, []);

  const fetchMfaStatus = async () => {
    try {
      const response = await api.get('/auth/mfa/status');
      setMfaEnabled(response.data.mfa_enabled);
      setBackupCodesRemaining(response.data.backup_codes_remaining || 0);
    } catch (error) {
      console.error('Failed to fetch MFA status:', error);
    }
  };

  const handleSetupMfa = async () => {
    if (!password) {
      Alert.alert('Error', 'Please enter your password to setup MFA');
      return;
    }
    
    setMfaLoading(true);
    try {
      const response = await api.post('/auth/mfa/setup', { password });
      setMfaQrCode(response.data.qr_code);
      setMfaSecret(response.data.secret);
      setShowMfaSetup(true);
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to setup MFA');
    } finally {
      setMfaLoading(false);
      setPassword('');
    }
  };

  const handleVerifyMfaSetup = async () => {
    if (!mfaCode || mfaCode.length !== 6) {
      Alert.alert('Error', 'Please enter a valid 6-digit code');
      return;
    }
    
    setMfaLoading(true);
    try {
      const response = await api.post('/auth/mfa/verify-setup', { code: mfaCode });
      setBackupCodes(response.data.backup_codes);
      setShowBackupCodes(true);
      setShowMfaSetup(false);
      setMfaEnabled(true);
      setMfaCode('');
      Alert.alert('Success', 'MFA has been enabled! Please save your backup codes.');
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Invalid verification code');
    } finally {
      setMfaLoading(false);
    }
  };

  const handleDisableMfa = () => {
    Alert.prompt(
      'Disable MFA',
      'Enter your current MFA code to disable two-factor authentication:',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Disable',
          style: 'destructive',
          onPress: async (code) => {
            if (!code || code.length !== 6) {
              Alert.alert('Error', 'Please enter a valid 6-digit code');
              return;
            }
            
            Alert.prompt(
              'Confirm Password',
              'Enter your password to confirm:',
              [
                { text: 'Cancel', style: 'cancel' },
                {
                  text: 'Confirm',
                  onPress: async (pwd) => {
                    try {
                      await api.post('/auth/mfa/disable', { password: pwd, mfa_code: code });
                      setMfaEnabled(false);
                      Alert.alert('Success', 'MFA has been disabled');
                    } catch (error: any) {
                      Alert.alert('Error', error.response?.data?.detail || 'Failed to disable MFA');
                    }
                  }
                }
              ],
              'secure-text'
            );
          }
        }
      ],
      'plain-text'
    );
  };

  const handleUpdateLinkedIn = async () => {
    try {
      await api.put('/auth/linkedin', null, {
        params: { linkedin_url: linkedinUrl },
      });
      Alert.alert(t('common.success'), 'LinkedIn URL updated');
    } catch (error) {
      Alert.alert(t('common.error'), 'Failed to update LinkedIn URL');
    }
  };

  const handleUpdateNotifications = async () => {
    try {
      await api.put('/auth/preferences', notifications);
      Alert.alert(t('common.success'), t('profile.savePreferences') + ' updated');
    } catch (error) {
      Alert.alert(t('common.error'), 'Failed to update preferences');
    }
  };

  const handleChangeLanguage = async (lang: string) => {
    await changeLanguage(lang);
    Alert.alert(t('common.success'), `Language changed to ${lang === 'de' ? 'Deutsch' : 'English'}`);
  };

  const handleLogout = () => {
    Alert.alert(t('auth.logout'), t('auth.logoutConfirm'), [
      { text: t('common.cancel'), style: 'cancel' },
      {
        text: t('auth.logout'),
        style: 'destructive',
        onPress: async () => {
          try {
            await api.post('/auth/logout');
          } catch (e) {
            // Ignore logout API errors
          }
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
          <UserIcon size={48} color={colors.accent} />
        </View>
        <Text style={styles.name}>{user?.name}</Text>
        <Text style={styles.email}>{user?.email}</Text>
        <View style={styles.roleBadge}>
          <Text style={styles.roleText}>{user?.role}</Text>
        </View>
      </View>

      {/* Security Section - MFA */}
      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <ShieldCheckIcon size={24} color={colors.primary} />
          <Text style={styles.sectionTitle}>Security</Text>
        </View>
        
        <View style={styles.mfaContainer}>
          <View style={styles.mfaInfo}>
            <DevicePhoneMobileIcon size={24} color={mfaEnabled ? colors.success : colors.textLight} />
            <View style={styles.mfaTextContainer}>
              <Text style={styles.mfaTitle}>Two-Factor Authentication</Text>
              <Text style={[styles.mfaStatus, { color: mfaEnabled ? colors.success : colors.textLight }]}>
                {mfaEnabled ? '✓ Enabled' : 'Not enabled'}
              </Text>
              {mfaEnabled && backupCodesRemaining > 0 && (
                <Text style={styles.backupCodesInfo}>
                  {backupCodesRemaining} backup codes remaining
                </Text>
              )}
            </View>
          </View>
          
          {!mfaEnabled ? (
            <View style={styles.mfaSetupContainer}>
              <Text style={styles.mfaDescription}>
                Add an extra layer of security to your account by enabling two-factor authentication.
              </Text>
              <View style={styles.passwordInputContainer}>
                <KeyIcon size={20} color={colors.textLight} />
                <TextInput
                  style={styles.passwordInput}
                  placeholder="Enter password to setup MFA"
                  value={password}
                  onChangeText={setPassword}
                  secureTextEntry
                  placeholderTextColor={colors.textLight}
                />
              </View>
              <TouchableOpacity
                style={styles.enableMfaButton}
                onPress={handleSetupMfa}
                disabled={mfaLoading}
              >
                {mfaLoading ? (
                  <ActivityIndicator color={colors.textWhite} />
                ) : (
                  <>
                    <QrCodeIcon size={20} color={colors.textWhite} />
                    <Text style={styles.enableMfaText}>Setup Two-Factor Auth</Text>
                  </>
                )}
              </TouchableOpacity>
            </View>
          ) : (
            <TouchableOpacity
              style={styles.disableMfaButton}
              onPress={handleDisableMfa}
            >
              <Text style={styles.disableMfaText}>Disable MFA</Text>
            </TouchableOpacity>
          )}
        </View>
      </View>

      {/* LinkedIn Section */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>{t('profile.linkedinProfile')}</Text>
        <View style={styles.inputContainer}>
          <TextInput
            style={styles.input}
            placeholder={t('profile.linkedinUrl')}
            value={linkedinUrl}
            onChangeText={setLinkedinUrl}
            placeholderTextColor={colors.textLight}
          />
        </View>
        <TouchableOpacity
          style={styles.saveButton}
          onPress={handleUpdateLinkedIn}
        >
          <Text style={styles.saveButtonText}>{t('profile.saveLinkedIn')}</Text>
        </TouchableOpacity>
      </View>

      {/* Language Section */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>{t('profile.language')}</Text>
        <View style={styles.languageButtons}>
          <TouchableOpacity
            style={[
              styles.languageButton,
              i18n.language === 'en' && styles.languageButtonActive,
            ]}
            onPress={() => handleChangeLanguage('en')}
          >
            <GlobeAltIcon 
              size={20} 
              color={i18n.language === 'en' ? colors.textWhite : colors.primary} 
            />
            <Text style={[
              styles.languageButtonText,
              i18n.language === 'en' && styles.languageButtonTextActive,
            ]}>
              {t('profile.english')}
            </Text>
          </TouchableOpacity>
          
          <TouchableOpacity
            style={[
              styles.languageButton,
              i18n.language === 'de' && styles.languageButtonActive,
            ]}
            onPress={() => handleChangeLanguage('de')}
          >
            <GlobeAltIcon 
              size={20} 
              color={i18n.language === 'de' ? colors.textWhite : colors.primary} 
            />
            <Text style={[
              styles.languageButtonText,
              i18n.language === 'de' && styles.languageButtonTextActive,
            ]}>
              {t('profile.german')}
            </Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Notifications Section */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>{t('profile.notificationPreferences')}</Text>
        
        <View style={styles.settingRow}>
          <View style={styles.settingInfo}>
            <BellIcon size={20} color={colors.primary} />
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
            <BellIcon size={20} color={colors.primary} />
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
            <BellIcon size={20} color={colors.primary} />
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
        <ArrowRightOnRectangleIcon size={20} color={colors.error} />
        <Text style={styles.logoutText}>Logout</Text>
      </TouchableOpacity>

      <View style={styles.footer}>
        <Text style={styles.footerText}>GroVELLOWS v2.0</Text>
        <Text style={styles.footerText}>German Construction Tenders</Text>
        <Text style={styles.footerTextSecure}>🔒 Secured with MFA & Encryption</Text>
      </View>

      {/* MFA Setup Modal */}
      <Modal
        visible={showMfaSetup}
        animationType="slide"
        transparent={true}
        onRequestClose={() => setShowMfaSetup(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Setup Two-Factor Authentication</Text>
            
            <Text style={styles.modalDescription}>
              1. Scan this QR code with your authenticator app (Google Authenticator, Authy, etc.)
            </Text>
            
            {mfaQrCode && (
              <View style={styles.qrCodeContainer}>
                <Image 
                  source={{ uri: mfaQrCode }} 
                  style={styles.qrCode}
                  resizeMode="contain"
                />
              </View>
            )}
            
            <Text style={styles.secretText}>
              Or enter this code manually: {mfaSecret}
            </Text>
            
            <Text style={styles.modalDescription}>
              2. Enter the 6-digit code from your authenticator app:
            </Text>
            
            <TextInput
              style={styles.codeInput}
              placeholder="000000"
              value={mfaCode}
              onChangeText={setMfaCode}
              keyboardType="number-pad"
              maxLength={6}
              placeholderTextColor={colors.textLight}
            />
            
            <View style={styles.modalButtons}>
              <TouchableOpacity
                style={styles.cancelButton}
                onPress={() => {
                  setShowMfaSetup(false);
                  setMfaCode('');
                }}
              >
                <Text style={styles.cancelButtonText}>Cancel</Text>
              </TouchableOpacity>
              
              <TouchableOpacity
                style={styles.verifyButton}
                onPress={handleVerifyMfaSetup}
                disabled={mfaLoading || mfaCode.length !== 6}
              >
                {mfaLoading ? (
                  <ActivityIndicator color={colors.textWhite} />
                ) : (
                  <Text style={styles.verifyButtonText}>Verify & Enable</Text>
                )}
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* Backup Codes Modal */}
      <Modal
        visible={showBackupCodes}
        animationType="slide"
        transparent={true}
        onRequestClose={() => setShowBackupCodes(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>🔐 Backup Codes</Text>
            
            <Text style={styles.warningText}>
              ⚠️ Save these codes in a secure place. Each code can only be used once.
            </Text>
            
            <View style={styles.backupCodesContainer}>
              {backupCodes.map((code, index) => (
                <Text key={index} style={styles.backupCode}>
                  {code}
                </Text>
              ))}
            </View>
            
            <Text style={styles.modalDescription}>
              Use these codes if you lose access to your authenticator app.
            </Text>
            
            <TouchableOpacity
              style={styles.verifyButton}
              onPress={() => {
                setShowBackupCodes(false);
                fetchMfaStatus();
              }}
            >
              <Text style={styles.verifyButtonText}>I've Saved My Codes</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
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
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
    gap: 8,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: colors.text,
    marginBottom: 16,
  },
  mfaContainer: {
    backgroundColor: colors.background,
    borderRadius: 12,
    padding: 16,
  },
  mfaInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  mfaTextContainer: {
    marginLeft: 12,
    flex: 1,
  },
  mfaTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.text,
  },
  mfaStatus: {
    fontSize: 14,
    marginTop: 2,
  },
  backupCodesInfo: {
    fontSize: 12,
    color: colors.textLight,
    marginTop: 2,
  },
  mfaSetupContainer: {
    marginTop: 8,
  },
  mfaDescription: {
    fontSize: 14,
    color: colors.textLight,
    marginBottom: 12,
    lineHeight: 20,
  },
  passwordInputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.card,
    borderRadius: 8,
    paddingHorizontal: 12,
    marginBottom: 12,
  },
  passwordInput: {
    flex: 1,
    height: 44,
    marginLeft: 8,
    fontSize: 14,
    color: colors.text,
  },
  enableMfaButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.success,
    padding: 14,
    borderRadius: 8,
    gap: 8,
  },
  enableMfaText: {
    color: colors.textWhite,
    fontSize: 14,
    fontWeight: '600',
  },
  disableMfaButton: {
    padding: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.error,
    alignItems: 'center',
  },
  disableMfaText: {
    color: colors.error,
    fontSize: 14,
    fontWeight: '600',
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
  footerTextSecure: {
    fontSize: 12,
    color: colors.success,
    marginTop: 4,
  },
  languageButtons: {
    flexDirection: 'row',
    gap: 12,
  },
  languageButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.background,
    padding: 16,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: colors.border,
    gap: 8,
  },
  languageButtonActive: {
    backgroundColor: colors.secondary,
    borderColor: colors.secondary,
  },
  languageButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.primary,
  },
  languageButtonTextActive: {
    color: colors.textWhite,
  },
  // Modal styles
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.7)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  modalContent: {
    backgroundColor: colors.card,
    borderRadius: 16,
    padding: 24,
    width: '100%',
    maxWidth: 400,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: colors.text,
    textAlign: 'center',
    marginBottom: 16,
  },
  modalDescription: {
    fontSize: 14,
    color: colors.textLight,
    marginBottom: 12,
    lineHeight: 20,
  },
  qrCodeContainer: {
    alignItems: 'center',
    marginVertical: 16,
    backgroundColor: colors.textWhite,
    padding: 16,
    borderRadius: 12,
  },
  qrCode: {
    width: 200,
    height: 200,
  },
  secretText: {
    fontSize: 12,
    color: colors.textLight,
    textAlign: 'center',
    fontFamily: 'monospace',
    marginBottom: 16,
  },
  codeInput: {
    backgroundColor: colors.background,
    borderRadius: 8,
    padding: 16,
    fontSize: 24,
    textAlign: 'center',
    letterSpacing: 8,
    color: colors.text,
    marginBottom: 16,
  },
  modalButtons: {
    flexDirection: 'row',
    gap: 12,
  },
  cancelButton: {
    flex: 1,
    padding: 14,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
  },
  cancelButtonText: {
    color: colors.text,
    fontSize: 14,
    fontWeight: '600',
  },
  verifyButton: {
    flex: 1,
    backgroundColor: colors.primary,
    padding: 14,
    borderRadius: 8,
    alignItems: 'center',
  },
  verifyButtonText: {
    color: colors.accent,
    fontSize: 14,
    fontWeight: '600',
  },
  warningText: {
    fontSize: 14,
    color: colors.warning,
    backgroundColor: colors.warningLight,
    padding: 12,
    borderRadius: 8,
    marginBottom: 16,
    textAlign: 'center',
  },
  backupCodesContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 8,
    marginBottom: 16,
  },
  backupCode: {
    backgroundColor: colors.background,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 6,
    fontFamily: 'monospace',
    fontSize: 14,
    color: colors.text,
  },
});
