import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
  Platform,
  Alert,
} from 'react-native';
import { BellIcon, BellAlertIcon, BellSlashIcon, CheckCircleIcon, ExclamationCircleIcon } from 'react-native-heroicons/outline';
import { colors } from '../../utils/colors';
import { useNotifications } from '../../contexts/NotificationContext';
import api from '../../utils/api';

export default function PushNotificationSettings() {
  const { 
    expoPushToken, 
    permissionStatus, 
    registerForNotifications, 
    isRegistered 
  } = useNotifications();
  
  const [loading, setLoading] = useState(false);
  const [testLoading, setTestLoading] = useState(false);
  const [tokenStatus, setTokenStatus] = useState<{
    has_active_tokens: boolean;
    token_count: number;
    platforms: string[];
  } | null>(null);

  useEffect(() => {
    fetchTokenStatus();
  }, [isRegistered]);

  const fetchTokenStatus = async () => {
    try {
      const response = await api.get('/push-tokens/status');
      setTokenStatus(response.data);
    } catch (error) {
      console.log('Could not fetch push token status');
    }
  };

  const handleEnableNotifications = async () => {
    setLoading(true);
    try {
      await registerForNotifications();
      await fetchTokenStatus();
      
      if (Platform.OS === 'web') {
        Alert.alert(
          'Web Limitations',
          'Push notifications have limited support on web browsers. For the best experience, use the mobile app via Expo Go.',
          [{ text: 'OK' }]
        );
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to enable push notifications');
    } finally {
      setLoading(false);
    }
  };

  const handleTestNotification = async () => {
    setTestLoading(true);
    try {
      const response = await api.post('/notifications/test');
      
      if (response.data.sent_count > 0) {
        Alert.alert(
          'Test Sent',
          'A test notification was sent to your device. It may take a few seconds to arrive.',
          [{ text: 'OK' }]
        );
      } else {
        Alert.alert(
          'Test Failed',
          response.data.message || 'Could not send test notification. Make sure you have registered for notifications.',
          [{ text: 'OK' }]
        );
      }
    } catch (error: any) {
      Alert.alert(
        'Error',
        error.response?.data?.detail || 'Failed to send test notification'
      );
    } finally {
      setTestLoading(false);
    }
  };

  const getStatusColor = () => {
    if (tokenStatus?.has_active_tokens) return colors.success;
    if (permissionStatus === 'granted') return colors.warning;
    return colors.textLight;
  };

  const getStatusIcon = () => {
    if (tokenStatus?.has_active_tokens) {
      return <BellAlertIcon size={24} color={colors.success} />;
    }
    if (permissionStatus === 'denied') {
      return <BellSlashIcon size={24} color={colors.error} />;
    }
    return <BellIcon size={24} color={colors.textLight} />;
  };

  const getStatusText = () => {
    if (tokenStatus?.has_active_tokens) {
      return `Active on ${tokenStatus.token_count} device(s)`;
    }
    if (permissionStatus === 'granted') {
      return 'Permission granted, not registered';
    }
    if (permissionStatus === 'denied') {
      return 'Permission denied';
    }
    return 'Not enabled';
  };

  return (
    <View style={styles.container}>
      {/* Status Display */}
      <View style={styles.statusContainer}>
        <View style={styles.statusIconContainer}>
          {getStatusIcon()}
        </View>
        <View style={styles.statusTextContainer}>
          <Text style={styles.statusTitle}>Push Notifications</Text>
          <Text style={[styles.statusText, { color: getStatusColor() }]}>
            {getStatusText()}
          </Text>
          {Platform.OS === 'web' && (
            <Text style={styles.webNote}>
              Limited support on web - use mobile app for best experience
            </Text>
          )}
        </View>
      </View>

      {/* Info Cards */}
      <View style={styles.infoContainer}>
        <View style={styles.infoCard}>
          <CheckCircleIcon size={20} color={colors.success} />
          <Text style={styles.infoText}>Get instant alerts for new tenders</Text>
        </View>
        <View style={styles.infoCard}>
          <CheckCircleIcon size={20} color={colors.success} />
          <Text style={styles.infoText}>Never miss important deadlines</Text>
        </View>
        <View style={styles.infoCard}>
          <CheckCircleIcon size={20} color={colors.success} />
          <Text style={styles.infoText}>Stay updated on tender status changes</Text>
        </View>
      </View>

      {/* Action Buttons */}
      <View style={styles.buttonContainer}>
        {!tokenStatus?.has_active_tokens ? (
          <TouchableOpacity
            style={styles.enableButton}
            onPress={handleEnableNotifications}
            disabled={loading || permissionStatus === 'denied'}
          >
            {loading ? (
              <ActivityIndicator color={colors.textWhite} />
            ) : (
              <>
                <BellAlertIcon size={20} color={colors.textWhite} />
                <Text style={styles.enableButtonText}>
                  {permissionStatus === 'denied' 
                    ? 'Permission Denied' 
                    : 'Enable Push Notifications'}
                </Text>
              </>
            )}
          </TouchableOpacity>
        ) : (
          <View style={styles.enabledContainer}>
            <View style={styles.enabledBadge}>
              <CheckCircleIcon size={20} color={colors.success} />
              <Text style={styles.enabledText}>Notifications Enabled</Text>
            </View>
            
            <TouchableOpacity
              style={styles.testButton}
              onPress={handleTestNotification}
              disabled={testLoading}
            >
              {testLoading ? (
                <ActivityIndicator color={colors.primary} />
              ) : (
                <>
                  <BellIcon size={18} color={colors.primary} />
                  <Text style={styles.testButtonText}>Send Test Notification</Text>
                </>
              )}
            </TouchableOpacity>
          </View>
        )}
      </View>

      {/* Device Info */}
      {tokenStatus?.has_active_tokens && tokenStatus.platforms.length > 0 && (
        <View style={styles.deviceInfo}>
          <Text style={styles.deviceInfoTitle}>Registered Platforms:</Text>
          <View style={styles.platformTags}>
            {tokenStatus.platforms.map((platform, index) => (
              <View key={index} style={styles.platformTag}>
                <Text style={styles.platformTagText}>
                  {platform.charAt(0).toUpperCase() + platform.slice(1)}
                </Text>
              </View>
            ))}
          </View>
        </View>
      )}

      {/* Permission Denied Help */}
      {permissionStatus === 'denied' && (
        <View style={styles.helpContainer}>
          <ExclamationCircleIcon size={20} color={colors.warning} />
          <Text style={styles.helpText}>
            Notification permission was denied. To enable notifications, go to your device settings and allow notifications for this app.
          </Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginTop: 8,
  },
  statusContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  statusIconContainer: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: colors.background,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  statusTextContainer: {
    flex: 1,
  },
  statusTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.text,
  },
  statusText: {
    fontSize: 14,
    marginTop: 2,
  },
  webNote: {
    fontSize: 12,
    color: colors.textLight,
    marginTop: 4,
    fontStyle: 'italic',
  },
  infoContainer: {
    paddingVertical: 12,
  },
  infoCard: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
    gap: 10,
  },
  infoText: {
    fontSize: 14,
    color: colors.text,
  },
  buttonContainer: {
    paddingVertical: 12,
  },
  enableButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.primary,
    paddingVertical: 14,
    borderRadius: 12,
    gap: 8,
  },
  enableButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.textWhite,
  },
  enabledContainer: {
    gap: 12,
  },
  enabledBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.successLight,
    paddingVertical: 12,
    borderRadius: 12,
    gap: 8,
  },
  enabledText: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.success,
  },
  testButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.background,
    paddingVertical: 12,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.primary,
    gap: 8,
  },
  testButtonText: {
    fontSize: 14,
    fontWeight: '500',
    color: colors.primary,
  },
  deviceInfo: {
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  deviceInfoTitle: {
    fontSize: 12,
    color: colors.textLight,
    marginBottom: 8,
  },
  platformTags: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  platformTag: {
    backgroundColor: colors.primaryLight,
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
  },
  platformTagText: {
    fontSize: 12,
    color: colors.primary,
    fontWeight: '500',
  },
  helpContainer: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    backgroundColor: colors.warningLight,
    padding: 12,
    borderRadius: 8,
    marginTop: 12,
    gap: 10,
  },
  helpText: {
    flex: 1,
    fontSize: 13,
    color: colors.warning,
    lineHeight: 18,
  },
});
