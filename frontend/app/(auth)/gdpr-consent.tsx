import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Switch,
  Alert,
} from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../../utils/colors';
import AsyncStorage from '@react-native-async-storage/async-storage';
import api from '../../utils/api';

export default function GDPRConsentScreen() {
  const router = useRouter();
  const params = useLocalSearchParams();
  const [consents, setConsents] = useState({
    dataProcessing: false,
    dataStorage: false,
    analytics: false,
    marketing: false,
  });

  const allRequired = consents.dataProcessing && consents.dataStorage;

  const handleAcceptAll = () => {
    setConsents({
      dataProcessing: true,
      dataStorage: true,
      analytics: true,
      marketing: true,
    });
  };

  const handleContinue = async () => {
    if (!allRequired) {
      Alert.alert(
        'Erforderliche Zustimmung',
        'Bitte stimmen Sie den erforderlichen Datenschutzbestimmungen zu, um fortzufahren.'
      );
      return;
    }

    try {
      // Save consent to backend
      await api.post('/auth/gdpr-consent', consents);
      
      // Save locally
      await AsyncStorage.setItem('gdpr_consent', JSON.stringify({
        ...consents,
        timestamp: new Date().toISOString(),
      }));

      // Navigate based on where user came from
      if (params.from === 'register') {
        router.replace('/(tabs)');
      } else {
        router.back();
      }
    } catch (error) {
      Alert.alert('Fehler', 'Fehler beim Speichern der Einwilligung');
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Datenschutz & Einwilligung</Text>
        <Text style={styles.subtitle}>DSGVO-Konform</Text>
      </View>

      <ScrollView style={styles.content}>
        <View style={styles.infoBox}>
          <Ionicons name="shield-checkmark" size={48} color={colors.secondary} />
          <Text style={styles.infoTitle}>Ihre Daten sind sicher</Text>
          <Text style={styles.infoText}>
            Wir nehmen den Schutz Ihrer persönlichen Daten sehr ernst und halten uns
            strikt an die Regeln der Datenschutzgesetze (DSGVO).
          </Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Erforderliche Einwilligungen</Text>
          
          <View style={styles.consentItem}>
            <View style={styles.consentHeader}>
              <View style={styles.consentInfo}>
                <Ionicons name="document-text" size={20} color={colors.primary} />
                <View style={styles.consentTextContainer}>
                  <Text style={styles.consentTitle}>Datenverarbeitung</Text>
                  <Text style={styles.requiredBadge}>Erforderlich</Text>
                </View>
              </View>
              <Switch
                value={consents.dataProcessing}
                onValueChange={(value) =>
                  setConsents({ ...consents, dataProcessing: value })
                }
                trackColor={{ false: colors.border, true: colors.secondary }}
                thumbColor={consents.dataProcessing ? colors.primary : colors.textLight}
              />
            </View>
            <Text style={styles.consentDescription}>
              Verarbeitung Ihrer personenbezogenen Daten (Name, E-Mail, Rolle) zur
              Bereitstellung der App-Funktionen und Verwaltung Ihres Kontos.
            </Text>
          </View>

          <View style={styles.consentItem}>
            <View style={styles.consentHeader}>
              <View style={styles.consentInfo}>
                <Ionicons name="server" size={20} color={colors.primary} />
                <View style={styles.consentTextContainer}>
                  <Text style={styles.consentTitle}>Datenspeicherung</Text>
                  <Text style={styles.requiredBadge}>Erforderlich</Text>
                </View>
              </View>
              <Switch
                value={consents.dataStorage}
                onValueChange={(value) =>
                  setConsents({ ...consents, dataStorage: value })
                }
                trackColor={{ false: colors.border, true: colors.secondary }}
                thumbColor={consents.dataStorage ? colors.primary : colors.textLight}
              />
            </View>
            <Text style={styles.consentDescription}>
              Speicherung Ihrer Daten auf sicheren Servern in Deutschland für die Dauer
              Ihrer Nutzung der App.
            </Text>
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Optionale Einwilligungen</Text>
          
          <View style={styles.consentItem}>
            <View style={styles.consentHeader}>
              <View style={styles.consentInfo}>
                <Ionicons name="analytics" size={20} color={colors.textLight} />
                <View style={styles.consentTextContainer}>
                  <Text style={styles.consentTitle}>Analyse & Verbesserung</Text>
                  <Text style={styles.optionalBadge}>Optional</Text>
                </View>
              </View>
              <Switch
                value={consents.analytics}
                onValueChange={(value) =>
                  setConsents({ ...consents, analytics: value })
                }
                trackColor={{ false: colors.border, true: colors.secondary }}
                thumbColor={consents.analytics ? colors.primary : colors.textLight}
              />
            </View>
            <Text style={styles.consentDescription}>
              Anonymisierte Nutzungsdaten zur Verbesserung der App-Funktionen.
            </Text>
          </View>

          <View style={styles.consentItem}>
            <View style={styles.consentHeader}>
              <View style={styles.consentInfo}>
                <Ionicons name="notifications" size={20} color={colors.textLight} />
                <View style={styles.consentTextContainer}>
                  <Text style={styles.consentTitle}>Marketing-Mitteilungen</Text>
                  <Text style={styles.optionalBadge}>Optional</Text>
                </View>
              </View>
              <Switch
                value={consents.marketing}
                onValueChange={(value) =>
                  setConsents({ ...consents, marketing: value })
                }
                trackColor={{ false: colors.border, true: colors.secondary }}
                thumbColor={consents.marketing ? colors.primary : colors.textLight}
              />
            </View>
            <Text style={styles.consentDescription}>
              Informationen über neue Funktionen und Updates per E-Mail.
            </Text>
          </View>
        </View>

        <View style={styles.infoSection}>
          <Text style={styles.infoSectionTitle}>Ihre Rechte nach DSGVO:</Text>
          <Text style={styles.bulletPoint}>• Recht auf Auskunft über Ihre Daten</Text>
          <Text style={styles.bulletPoint}>• Recht auf Berichtigung oder Löschung</Text>
          <Text style={styles.bulletPoint}>• Recht auf Einschränkung der Verarbeitung</Text>
          <Text style={styles.bulletPoint}>• Recht auf Datenübertragbarkeit</Text>
          <Text style={styles.bulletPoint}>• Widerspruchsrecht</Text>
          <Text style={styles.bulletPoint}>• Beschwerderecht bei einer Aufsichtsbehörde</Text>
        </View>

        <TouchableOpacity
          style={styles.linkButton}
          onPress={() => {
            // TODO: Navigate to full privacy policy
            Alert.alert(
              'Datenschutzerklärung',
              'Hier würde die vollständige Datenschutzerklärung angezeigt werden.'
            );
          }}
        >
          <Text style={styles.linkText}>Vollständige Datenschutzerklärung lesen</Text>
          <Ionicons name="chevron-forward" size={16} color={colors.secondary} />
        </TouchableOpacity>
      </ScrollView>

      <View style={styles.footer}>
        <TouchableOpacity
          style={styles.acceptAllButton}
          onPress={handleAcceptAll}
        >
          <Text style={styles.acceptAllText}>Alle akzeptieren</Text>
        </TouchableOpacity>
        
        <TouchableOpacity
          style={[styles.continueButton, !allRequired && styles.continueButtonDisabled]}
          onPress={handleContinue}
          disabled={!allRequired}
        >
          <Text style={styles.continueButtonText}>
            {allRequired ? 'Fortfahren' : 'Erforderliche Zustimmung fehlt'}
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  header: {
    backgroundColor: colors.primary,
    padding: 24,
    paddingTop: 60,
    alignItems: 'center',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: colors.textWhite,
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 14,
    color: colors.secondary,
  },
  content: {
    flex: 1,
  },
  infoBox: {
    backgroundColor: colors.card,
    padding: 24,
    margin: 16,
    borderRadius: 12,
    alignItems: 'center',
  },
  infoTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: colors.text,
    marginTop: 16,
    marginBottom: 8,
  },
  infoText: {
    fontSize: 14,
    color: colors.textLight,
    textAlign: 'center',
    lineHeight: 20,
  },
  section: {
    backgroundColor: colors.card,
    padding: 20,
    marginTop: 16,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: colors.text,
    marginBottom: 16,
  },
  consentItem: {
    marginBottom: 20,
    paddingBottom: 20,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  consentHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  consentInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  consentTextContainer: {
    marginLeft: 12,
    flex: 1,
  },
  consentTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 4,
  },
  requiredBadge: {
    fontSize: 11,
    color: colors.error,
    fontWeight: '600',
  },
  optionalBadge: {
    fontSize: 11,
    color: colors.textLight,
    fontWeight: '600',
  },
  consentDescription: {
    fontSize: 13,
    color: colors.textLight,
    lineHeight: 18,
    marginLeft: 32,
  },
  infoSection: {
    backgroundColor: colors.card,
    padding: 20,
    margin: 16,
    borderRadius: 12,
  },
  infoSectionTitle: {
    fontSize: 14,
    fontWeight: 'bold',
    color: colors.text,
    marginBottom: 12,
  },
  bulletPoint: {
    fontSize: 13,
    color: colors.textLight,
    marginBottom: 6,
    lineHeight: 18,
  },
  linkButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    marginBottom: 80,
  },
  linkText: {
    fontSize: 14,
    color: colors.secondary,
    fontWeight: '600',
    marginRight: 4,
  },
  footer: {
    backgroundColor: colors.card,
    padding: 16,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  acceptAllButton: {
    backgroundColor: colors.background,
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    marginBottom: 12,
    borderWidth: 1,
    borderColor: colors.secondary,
  },
  acceptAllText: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.secondary,
  },
  continueButton: {
    backgroundColor: colors.secondary,
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
  },
  continueButtonDisabled: {
    backgroundColor: colors.border,
  },
  continueButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.textWhite,
  },
});