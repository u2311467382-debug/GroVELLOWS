import { Tabs } from 'expo-router';
import { colors } from '../../utils/colors';
import { useTranslation } from 'react-i18next';
import { DocumentTextIcon, NewspaperIcon, BuildingOfficeIcon, StarIcon, UserIcon } from 'react-native-heroicons/outline';

export default function TabsLayout() {
  const { t } = useTranslation();
  
  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: colors.accent,
        tabBarInactiveTintColor: colors.textLight,
        tabBarStyle: {
          backgroundColor: colors.primary,
          borderTopColor: colors.primaryLight,
          borderTopWidth: 1,
          height: 65,
          paddingBottom: 8,
          paddingTop: 8,
        },
        headerStyle: {
          backgroundColor: colors.primary,
        },
        headerTintColor: colors.accent,
        headerTitleStyle: {
          fontWeight: 'bold',
        },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: t('tenders.title'),
          headerShown: false,
          tabBarIcon: ({ color, size }) => (
            <DocumentTextIcon size={20} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="news"
        options={{
          title: t('news.title'),
          tabBarIcon: ({ color, size }) => (
            <NewspaperIcon size={20} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="projects"
        options={{
          title: t('developerProjects.title'),
          tabBarIcon: ({ color, size }) => (
            <BuildingOfficeIcon size={20} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="favorites"
        options={{
          title: t('favorites.title'),
          tabBarIcon: ({ color, size }) => (
            <StarIcon size={20} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: t('profile.title'),
          tabBarIcon: ({ color, size }) => (
            <UserIcon size={20} color={color} />
          ),
        }}
      />
    </Tabs>
  );
}
