import React from 'react';
import { Platform, Text, StyleSheet, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

// Icon name to emoji mapping for web fallback
const iconEmojiMap: { [key: string]: string } = {
  'documents-outline': '📄',
  'document-text': '📄',
  'document-text-outline': '📄',
  'mail-outline': '✉️',
  'lock-closed-outline': '🔒',
  'person-outline': '👤',
  'briefcase-outline': '💼',
  'arrow-back': '←',
  'chevron-forward': '›',
  'chevron-back': '‹',
  'shield-checkmark': '🛡️',
  'document-text': '📝',
  'server': '🖥️',
  'analytics': '📊',
  'notifications': '🔔',
  'home': '🏠',
  'home-outline': '🏠',
  'search': '🔍',
  'search-outline': '🔍',
  'heart': '❤️',
  'heart-outline': '🤍',
  'settings': '⚙️',
  'settings-outline': '⚙️',
  'newspaper': '📰',
  'newspaper-outline': '📰',
  'business': '🏢',
  'business-outline': '🏢',
  'star': '⭐',
  'star-outline': '☆',
  'bookmark': '🔖',
  'bookmark-outline': '🔖',
  'calendar': '📅',
  'calendar-outline': '📅',
  'location': '📍',
  'location-outline': '📍',
  'call': '📞',
  'call-outline': '📞',
  'chatbubble': '💬',
  'chatbubble-outline': '💬',
  'send': '📤',
  'send-outline': '📤',
  'add': '+',
  'add-outline': '+',
  'close': '✕',
  'close-outline': '✕',
  'checkmark': '✓',
  'checkmark-outline': '✓',
  'ellipsis-horizontal': '⋯',
  'ellipsis-vertical': '⋮',
  'share': '↗️',
  'share-outline': '↗️',
  'trash': '🗑️',
  'trash-outline': '🗑️',
  'pencil': '✏️',
  'create-outline': '✏️',
  'eye': '👁️',
  'eye-outline': '👁️',
  'eye-off': '🙈',
  'eye-off-outline': '🙈',
  'flag': '🚩',
  'flag-outline': '🚩',
  'link': '🔗',
  'link-outline': '🔗',
  'copy': '📋',
  'copy-outline': '📋',
  'refresh': '🔄',
  'refresh-outline': '🔄',
  'filter': '🔧',
  'filter-outline': '🔧',
  'download': '⬇️',
  'download-outline': '⬇️',
  'cloud-upload': '☁️',
  'cloud-upload-outline': '☁️',
  'log-out': '🚪',
  'log-out-outline': '🚪',
  'information-circle': 'ℹ️',
  'information-circle-outline': 'ℹ️',
  'warning': '⚠️',
  'warning-outline': '⚠️',
  'alert-circle': '❗',
  'alert-circle-outline': '❗',
  'time': '⏰',
  'time-outline': '⏰',
  'cash': '💰',
  'cash-outline': '💰',
  'globe': '🌐',
  'globe-outline': '🌐',
  'people': '👥',
  'people-outline': '👥',
  'person': '👤',
  'person-outline': '👤',
  'menu': '☰',
  'menu-outline': '☰',
};

interface AppIconProps {
  name: keyof typeof Ionicons.glyphMap;
  size?: number;
  color?: string;
  style?: any;
}

export const AppIcon: React.FC<AppIconProps> = ({ name, size = 24, color = '#000', style }) => {
  // On native platforms, use Ionicons
  if (Platform.OS !== 'web') {
    return <Ionicons name={name} size={size} color={color} style={style} />;
  }
  
  // On web, use emoji fallback
  const emoji = iconEmojiMap[name] || '•';
  
  return (
    <View style={[styles.iconContainer, style, { width: size, height: size }]}>
      <Text style={[styles.emoji, { fontSize: size * 0.7, color }]}>
        {emoji}
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  iconContainer: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  emoji: {
    textAlign: 'center',
  },
});

export default AppIcon;
