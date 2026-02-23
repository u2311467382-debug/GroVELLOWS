import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';
import Constants from 'expo-constants';
import { Platform } from 'react-native';
import api from '../utils/api';

// Configure notification handler
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
});

export interface NotificationData {
  screen?: string;
  tenderId?: string;
  type?: string;
  [key: string]: any;
}

/**
 * Register for push notifications and get the Expo push token
 */
export async function registerForPushNotificationsAsync(): Promise<string | null> {
  let token: string | null = null;

  // Only works on physical devices
  if (!Device.isDevice) {
    console.log('Push notifications require a physical device');
    return null;
  }

  // Check existing permissions
  const { status: existingStatus } = await Notifications.getPermissionsAsync();
  let finalStatus = existingStatus;

  // Request permissions if not granted
  if (existingStatus !== 'granted') {
    const { status } = await Notifications.requestPermissionsAsync();
    finalStatus = status;
  }

  if (finalStatus !== 'granted') {
    console.log('Push notification permission denied');
    return null;
  }

  try {
    // Get project ID from expo config
    const projectId = Constants.expoConfig?.extra?.eas?.projectId 
      || Constants.expoConfig?.extra?.projectId
      || 'grovellows';

    // Get Expo push token
    const tokenResponse = await Notifications.getExpoPushTokenAsync({
      projectId: projectId,
    });
    
    token = tokenResponse.data;
    console.log('Expo Push Token:', token);
  } catch (error) {
    console.error('Error getting push token:', error);
  }

  // Configure Android notification channel
  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('default', {
      name: 'Default',
      importance: Notifications.AndroidImportance.MAX,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: '#C9A862',
    });

    // Create channel for new tenders
    await Notifications.setNotificationChannelAsync('new-tenders', {
      name: 'New Tenders',
      importance: Notifications.AndroidImportance.HIGH,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: '#C9A862',
      description: 'Notifications for new tender alerts',
    });
  }

  return token;
}

/**
 * Register push token with the backend
 */
export async function registerPushTokenWithBackend(
  userId: string,
  token: string
): Promise<boolean> {
  try {
    const response = await api.post('/push-tokens', {
      user_id: userId,
      expo_push_token: token,
      platform: Platform.OS,
    });
    
    console.log('Push token registered with backend:', response.data);
    return true;
  } catch (error) {
    console.error('Error registering push token:', error);
    return false;
  }
}

/**
 * Unregister push token (when user logs out)
 */
export async function unregisterPushToken(userId: string): Promise<boolean> {
  try {
    await api.delete(`/push-tokens/${userId}`);
    console.log('Push token unregistered');
    return true;
  } catch (error) {
    console.error('Error unregistering push token:', error);
    return false;
  }
}

/**
 * Add listener for received notifications (app in foreground)
 */
export function addNotificationReceivedListener(
  callback: (notification: Notifications.Notification) => void
): Notifications.Subscription {
  return Notifications.addNotificationReceivedListener(callback);
}

/**
 * Add listener for notification responses (user tapped notification)
 */
export function addNotificationResponseListener(
  callback: (response: Notifications.NotificationResponse) => void
): Notifications.Subscription {
  return Notifications.addNotificationResponseReceivedListener(callback);
}

/**
 * Remove notification subscription
 */
export function removeNotificationSubscription(
  subscription: Notifications.Subscription
): void {
  Notifications.removeNotificationSubscription(subscription);
}

/**
 * Get notification permissions status
 */
export async function getNotificationPermissions(): Promise<string> {
  const { status } = await Notifications.getPermissionsAsync();
  return status;
}

/**
 * Schedule a local notification
 */
export async function scheduleLocalNotification(
  title: string,
  body: string,
  data?: NotificationData,
  seconds: number = 1
): Promise<string> {
  const identifier = await Notifications.scheduleNotificationAsync({
    content: {
      title,
      body,
      data,
      sound: true,
    },
    trigger: {
      seconds,
    },
  });
  
  return identifier;
}

/**
 * Cancel all scheduled notifications
 */
export async function cancelAllNotifications(): Promise<void> {
  await Notifications.cancelAllScheduledNotificationsAsync();
}

/**
 * Get badge count
 */
export async function getBadgeCount(): Promise<number> {
  return await Notifications.getBadgeCountAsync();
}

/**
 * Set badge count
 */
export async function setBadgeCount(count: number): Promise<boolean> {
  return await Notifications.setBadgeCountAsync(count);
}
