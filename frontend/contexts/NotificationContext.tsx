import React, { createContext, useContext, useEffect, useState, useRef, ReactNode } from 'react';
import * as Notifications from 'expo-notifications';
import { useRouter } from 'expo-router';
import { Platform } from 'react-native';
import {
  registerForPushNotificationsAsync,
  registerPushTokenWithBackend,
  addNotificationReceivedListener,
  addNotificationResponseListener,
  removeNotificationSubscription,
  getNotificationPermissions,
} from '../services/notifications';
import { useAuth } from './AuthContext';

interface NotificationContextType {
  expoPushToken: string | null;
  notification: Notifications.Notification | null;
  permissionStatus: string;
  registerForNotifications: () => Promise<void>;
  isRegistered: boolean;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export function NotificationProvider({ children }: { children: ReactNode }) {
  const [expoPushToken, setExpoPushToken] = useState<string | null>(null);
  const [notification, setNotification] = useState<Notifications.Notification | null>(null);
  const [permissionStatus, setPermissionStatus] = useState<string>('undetermined');
  const [isRegistered, setIsRegistered] = useState<boolean>(false);
  
  const notificationListener = useRef<Notifications.Subscription>();
  const responseListener = useRef<Notifications.Subscription>();
  
  const { user, token } = useAuth();
  const router = useRouter();

  // Register for push notifications when user logs in
  const registerForNotifications = async () => {
    try {
      console.log('Registering for push notifications...');
      
      // Get expo push token
      const pushToken = await registerForPushNotificationsAsync();
      
      if (pushToken) {
        setExpoPushToken(pushToken);
        console.log('Got push token:', pushToken);
        
        // Register with backend if user is logged in
        if (user && token) {
          const success = await registerPushTokenWithBackend(user.id, pushToken);
          setIsRegistered(success);
          console.log('Backend registration:', success ? 'Success' : 'Failed');
        }
      }
      
      // Update permission status
      const status = await getNotificationPermissions();
      setPermissionStatus(status);
      
    } catch (error) {
      console.error('Error registering for notifications:', error);
    }
  };

  // Handle notification received (app in foreground)
  useEffect(() => {
    notificationListener.current = addNotificationReceivedListener((notification) => {
      console.log('Notification received:', notification);
      setNotification(notification);
    });

    // Handle notification response (user tapped notification)
    responseListener.current = addNotificationResponseListener((response) => {
      console.log('Notification tapped:', response);
      
      const data = response.notification.request.content.data;
      
      // Navigate based on notification data
      if (data?.screen) {
        switch (data.screen) {
          case 'Tenders':
            if (data.tenderId) {
              router.push(`/tender/${data.tenderId}`);
            } else {
              router.push('/(tabs)');
            }
            break;
          case 'Favorites':
            router.push('/(tabs)/favorites');
            break;
          case 'Profile':
            router.push('/(tabs)/profile');
            break;
          default:
            router.push('/(tabs)');
        }
      }
    });

    return () => {
      if (notificationListener.current) {
        removeNotificationSubscription(notificationListener.current);
      }
      if (responseListener.current) {
        removeNotificationSubscription(responseListener.current);
      }
    };
  }, [router]);

  // Register when user logs in
  useEffect(() => {
    if (user && token && !isRegistered) {
      registerForNotifications();
    }
  }, [user, token]);

  // Check initial permission status
  useEffect(() => {
    getNotificationPermissions().then(setPermissionStatus);
  }, []);

  return (
    <NotificationContext.Provider
      value={{
        expoPushToken,
        notification,
        permissionStatus,
        registerForNotifications,
        isRegistered,
      }}
    >
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotifications() {
  const context = useContext(NotificationContext);
  if (context === undefined) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return context;
}
