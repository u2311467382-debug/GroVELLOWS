import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  ActivityIndicator,
  Modal,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '../../contexts/AuthContext';
import { colors } from '../../utils/colors';
import { fonts } from '../../utils/fonts';
import { DocumentTextIcon, EnvelopeIcon, LockClosedIcon, ShieldCheckIcon, DevicePhoneMobileIcon } from 'react-native-heroicons/outline';
import { useTranslation } from 'react-i18next';
import api from '../../utils/api';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { login, setUser, setToken } = useAuth();
  const router = useRouter();
  const { t } = useTranslation();
  
  // MFA State
  const [showMfaModal, setShowMfaModal] = useState(false);
  const [mfaCode, setMfaCode] = useState('');
  const [mfaLoading, setMfaLoading] = useState(false);
  const [pendingEmail, setPendingEmail] = useState('');
  const [pendingPassword, setPendingPassword] = useState('');

  const handleLogin = async () => {
    if (!email || !password) {
      Alert.alert(t('common.error'), t('errors.fillAllFields'));
      return;
    }

    setLoading(true);
    try {
      // Call login API directly to check for MFA requirement
      const response = await api.post('/auth/login', { email, password });
      
      // Check if MFA is required
      if (response.data.mfa_required) {
        // Store credentials temporarily for MFA verification
        setPendingEmail(email);
        setPendingPassword(password);
        setShowMfaModal(true);
        setLoading(false);
        return;
      }
      
      // MFA not required or already included - proceed with login
      if (response.data.access_token) {
        // Store token and user data
        await setToken(response.data.access_token);
        await setUser(response.data.user);
        router.replace('/(tabs)');
      }
    } catch (error: any) {
      const message = error.response?.data?.detail || error.message || 'Login failed';
      Alert.alert(t('errors.loginFailed'), message);
    } finally {
      setLoading(false);
    }
  };

  const handleMfaVerify = async () => {
    if (!mfaCode || mfaCode.length !== 6) {
      Alert.alert('Error', 'Please enter a valid 6-digit code');
      return;
    }

    setMfaLoading(true);
    try {
      // Retry login with MFA code
      const response = await api.post('/auth/login', {
        email: pendingEmail,
        password: pendingPassword,
        mfa_code: mfaCode,
      });
      
      if (response.data.access_token) {
        // Store token and user data
        await setToken(response.data.access_token);
        await setUser(response.data.user);
        setShowMfaModal(false);
        setMfaCode('');
        router.replace('/(tabs)');
      }
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Invalid MFA code';
      Alert.alert('Verification Failed', message);
    } finally {
      setMfaLoading(false);
    }
  };

  const handleCancelMfa = () => {
    setShowMfaModal(false);
    setMfaCode('');
    setPendingEmail('');
    setPendingPassword('');
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      style={styles.container}
    >
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.header}>
          <DocumentTextIcon size={80} color={colors.secondary} />
          <Text style={styles.title}>{t('app.name')}</Text>
          <Text style={styles.subtitle}>{t('app.subtitle')}</Text>
        </View>

        <View style={styles.form}>
          <View style={styles.inputContainer}>
            <EnvelopeIcon size={20} color={colors.textLight} style={styles.inputIcon} />
            <TextInput
              style={styles.input}
              placeholder={t('auth.email')}
              value={email}
              onChangeText={setEmail}
              autoCapitalize="none"
              keyboardType="email-address"
              placeholderTextColor={colors.textLight}
            />
          </View>

          <View style={styles.inputContainer}>
            <LockClosedIcon size={20} color={colors.textLight} style={styles.inputIcon} />
            <TextInput
              style={styles.input}
              placeholder={t('auth.password')}
              value={password}
              onChangeText={setPassword}
              secureTextEntry
              placeholderTextColor={colors.textLight}
            />
          </View>

          <TouchableOpacity
            style={[styles.button, loading && styles.buttonDisabled]}
            onPress={handleLogin}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color={colors.card} />
            ) : (
              <Text style={styles.buttonText}>{t('auth.login')}</Text>
            )}
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.linkButton}
            onPress={() => router.push('/(auth)/register')}
          >
            <Text style={styles.linkText}>{t('auth.dontHaveAccount')}</Text>
          </TouchableOpacity>
          
          {/* Security Badge */}
          <View style={styles.securityBadge}>
            <ShieldCheckIcon size={16} color={colors.success} />
            <Text style={styles.securityText}>Secured with MFA & Encryption</Text>
          </View>
        </View>
      </ScrollView>

      {/* MFA Verification Modal */}
      <Modal
        visible={showMfaModal}
        animationType="slide"
        transparent={true}
        onRequestClose={handleCancelMfa}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <DevicePhoneMobileIcon size={48} color={colors.primary} />
              <Text style={styles.modalTitle}>Two-Factor Authentication</Text>
              <Text style={styles.modalSubtitle}>
                Enter the 6-digit code from your authenticator app
              </Text>
            </View>
            
            <TextInput
              style={styles.mfaInput}
              placeholder="000000"
              value={mfaCode}
              onChangeText={setMfaCode}
              keyboardType="number-pad"
              maxLength={6}
              placeholderTextColor={colors.textLight}
              autoFocus
            />
            
            <Text style={styles.helperText}>
              You can also use a backup code if you've lost access to your authenticator app.
            </Text>
            
            <View style={styles.modalButtons}>
              <TouchableOpacity
                style={styles.cancelButton}
                onPress={handleCancelMfa}
                disabled={mfaLoading}
              >
                <Text style={styles.cancelButtonText}>Cancel</Text>
              </TouchableOpacity>
              
              <TouchableOpacity
                style={[styles.verifyButton, mfaCode.length !== 6 && styles.verifyButtonDisabled]}
                onPress={handleMfaVerify}
                disabled={mfaLoading || mfaCode.length !== 6}
              >
                {mfaLoading ? (
                  <ActivityIndicator color={colors.textWhite} />
                ) : (
                  <Text style={styles.verifyButtonText}>Verify</Text>
                )}
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.primary,
  },
  scrollContent: {
    flexGrow: 1,
    justifyContent: 'center',
    padding: 24,
  },
  header: {
    alignItems: 'center',
    marginBottom: 48,
  },
  title: {
    fontSize: 32,
    fontFamily: fonts.bold,
    fontWeight: fonts.weight.bold as any,
    color: colors.secondary,
    marginTop: 16,
  },
  subtitle: {
    fontSize: 16,
    fontFamily: fonts.regular,
    fontWeight: fonts.weight.regular as any,
    color: colors.textWhite,
    marginTop: 8,
  },
  form: {
    width: '100%',
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    borderRadius: 12,
    marginBottom: 16,
    paddingHorizontal: 16,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.2)',
  },
  inputIcon: {
    marginRight: 12,
  },
  input: {
    flex: 1,
    height: 56,
    color: colors.card,
    fontSize: 16,
  },
  button: {
    backgroundColor: colors.secondary,
    borderRadius: 12,
    height: 56,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 8,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: colors.card,
    fontSize: 18,
    fontWeight: '600',
  },
  linkButton: {
    marginTop: 24,
    alignItems: 'center',
  },
  linkText: {
    color: colors.accent,
    fontSize: 16,
  },
  securityBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 32,
    gap: 8,
  },
  securityText: {
    color: colors.success,
    fontSize: 12,
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
  modalHeader: {
    alignItems: 'center',
    marginBottom: 24,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: colors.text,
    marginTop: 12,
    textAlign: 'center',
  },
  modalSubtitle: {
    fontSize: 14,
    color: colors.textLight,
    marginTop: 8,
    textAlign: 'center',
  },
  mfaInput: {
    backgroundColor: colors.background,
    borderRadius: 12,
    padding: 16,
    fontSize: 32,
    textAlign: 'center',
    letterSpacing: 12,
    color: colors.text,
    marginBottom: 16,
    fontWeight: 'bold',
  },
  helperText: {
    fontSize: 12,
    color: colors.textLight,
    textAlign: 'center',
    marginBottom: 24,
  },
  modalButtons: {
    flexDirection: 'row',
    gap: 12,
  },
  cancelButton: {
    flex: 1,
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
  },
  cancelButtonText: {
    color: colors.text,
    fontSize: 16,
    fontWeight: '600',
  },
  verifyButton: {
    flex: 1,
    backgroundColor: colors.primary,
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
  },
  verifyButtonDisabled: {
    opacity: 0.5,
  },
  verifyButtonText: {
    color: colors.accent,
    fontSize: 16,
    fontWeight: '600',
  },
});
