"use client";

import React, { useState } from "react";
import { User, Globe, PhoneCall, Trash2, Plus, Shield } from "lucide-react";
import { Modal } from "@/components/ui/modal";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { AlertBanner } from "@/components/ui/alert-banner";
import { EmptyState } from "@/components/ui/empty-state";
import { useAuth } from "@/lib/auth-context";
import { useLanguage } from "@/lib/i18n/language-context";
import { api, ApiEmergencyContact, ApiUserDetail } from "@/lib/api";
import { SupportedLanguage } from "@/lib/i18n/translations";

function ProfileModalContent({ user }: { user: ApiUserDetail }) {
  const { token, refreshUser } = useAuth();
  const { t, language, setLanguage, languages } = useLanguage();

  const [activeTab, setActiveTab] = useState<"profile" | "preferences" | "emergency">("profile");

  // Profile Form State initialized directly from user prop
  const [fullName, setFullName] = useState(user.profile?.full_name || "");
  const [phone, setPhone] = useState(user.profile?.phone_number || "");
  const [bloodGroup, setBloodGroup] = useState(user.profile?.blood_group || "");
  const [city, setCity] = useState(user.profile?.city || "");
  const [stateName, setStateName] = useState(user.profile?.state || "");
  const [pincode, setPincode] = useState(user.profile?.pincode || "");

  // Preferences Form State
  const [alertsEnabled, setAlertsEnabled] = useState(user.preferences?.emergency_alerts_enabled ?? true);
  const [locationEnabled, setLocationEnabled] = useState(user.preferences?.location_sharing_enabled ?? false);

  // Emergency Contacts State
  const [contacts, setContacts] = useState<ApiEmergencyContact[]>(user.emergency_contacts || []);
  const [showAddContact, setShowAddContact] = useState(false);
  const [contactName, setContactName] = useState("");
  const [contactRelation, setContactRelation] = useState("");
  const [contactPhone, setContactPhone] = useState("");
  const [contactPrimary, setContactPrimary] = useState(false);

  const [notice, setNotice] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setIsSaving(true);
    setNotice(null);
    try {
      await api.updateProfile(
        {
          full_name: fullName,
          phone_number: phone,
          blood_group: bloodGroup,
          city,
          state: stateName,
          pincode,
        },
        token
      );
      await refreshUser();
      setNotice({ type: "success", text: t.profile.savedSuccess });
    } catch (err: unknown) {
      setNotice({
        type: "error",
        text: err instanceof Error ? err.message : "Failed to update profile",
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleLanguageChange = async (newLang: SupportedLanguage) => {
    setLanguage(newLang);
    if (token) {
      try {
        await api.updatePreferences({ preferred_language: newLang }, token);
        await refreshUser();
      } catch (err) {
        console.warn("Could not sync preference with backend:", err);
      }
    }
  };

  const handleAddContact = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setIsSaving(true);
    setNotice(null);
    try {
      await api.addEmergencyContact(
        {
          name: contactName,
          relationship: contactRelation,
          phone_number: contactPhone,
          is_primary: contactPrimary,
        },
        token
      );
      const updated = await api.getEmergencyContacts(token);
      setContacts(updated);
      setContactName("");
      setContactRelation("");
      setContactPhone("");
      setContactPrimary(false);
      setShowAddContact(false);
      await refreshUser();
      setNotice({ type: "success", text: "Emergency contact registered" });
    } catch (err: unknown) {
      setNotice({
        type: "error",
        text: err instanceof Error ? err.message : "Failed to add emergency contact",
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteContact = async (contactId: string) => {
    if (!token) return;
    try {
      await api.deleteEmergencyContact(contactId, token);
      setContacts(contacts.filter((c) => c.id !== contactId));
      await refreshUser();
    } catch (err) {
      console.error("Delete contact error:", err);
    }
  };

  return (
    <>
      {/* Tabs */}
      <div className="flex border-b border-slate-200 mb-6 gap-2">
        <button
          onClick={() => {
            setNotice(null);
            setActiveTab("profile");
          }}
          className={`flex items-center gap-2 pb-3 px-3 text-sm font-semibold border-b-2 transition-all ${
            activeTab === "profile"
              ? "border-blue-600 text-blue-600"
              : "border-transparent text-slate-500 hover:text-slate-900"
          }`}
        >
          <User className="w-4 h-4" />
          {t.profile.title}
        </button>

        <button
          onClick={() => {
            setNotice(null);
            setActiveTab("preferences");
          }}
          className={`flex items-center gap-2 pb-3 px-3 text-sm font-semibold border-b-2 transition-all ${
            activeTab === "preferences"
              ? "border-blue-600 text-blue-600"
              : "border-transparent text-slate-500 hover:text-slate-900"
          }`}
        >
          <Globe className="w-4 h-4" />
          {t.preferences.title}
        </button>

        <button
          onClick={() => {
            setNotice(null);
            setActiveTab("emergency");
          }}
          className={`flex items-center gap-2 pb-3 px-3 text-sm font-semibold border-b-2 transition-all ${
            activeTab === "emergency"
              ? "border-blue-600 text-blue-600"
              : "border-transparent text-slate-500 hover:text-slate-900"
          }`}
        >
          <PhoneCall className="w-4 h-4" />
          {t.profile.emergencyContactsTitle}
        </button>
      </div>

      {notice && (
        <div className="mb-4">
          <AlertBanner variant={notice.type}>
            {notice.text}
          </AlertBanner>
        </div>
      )}

      {/* Tab 1: Personal Info */}
      {activeTab === "profile" && (
        <form onSubmit={handleSaveProfile} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label={t.profile.fullName}
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="e.g. Rahul Sharma"
            />
            <Input
              label={t.profile.phone}
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+91 98765 43210"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                {t.profile.bloodGroup}
              </label>
              <select
                value={bloodGroup}
                onChange={(e) => setBloodGroup(e.target.value)}
                className="w-full h-11 px-3.5 rounded-xl border border-slate-200 bg-white text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select</option>
                {["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"].map((bg) => (
                  <option key={bg} value={bg}>
                    {bg}
                  </option>
                ))}
              </select>
            </div>

            <Input
              label={t.profile.city}
              value={city}
              onChange={(e) => setCity(e.target.value)}
              placeholder="e.g. Chennai"
            />

            <Input
              label={t.profile.pincode}
              value={pincode}
              onChange={(e) => setPincode(e.target.value)}
              placeholder="600001"
            />
          </div>

          <Input
            label={t.profile.state}
            value={stateName}
            onChange={(e) => setStateName(e.target.value)}
            placeholder="Tamil Nadu"
          />

          <div className="pt-2 flex justify-end">
            <Button type="submit" isLoading={isSaving}>
              {t.common.save}
            </Button>
          </div>
        </form>
      )}

      {/* Tab 2: Preferences */}
      {activeTab === "preferences" && (
        <div className="space-y-6">
          <div>
            <label className="block text-sm font-semibold text-slate-900 mb-2">
              {t.preferences.preferredLanguage}
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
              {languages.map((l) => (
                <button
                  key={l.code}
                  type="button"
                  onClick={() => handleLanguageChange(l.code)}
                  className={`p-3 rounded-xl border text-left flex flex-col transition-all ${
                    language === l.code
                      ? "border-blue-600 bg-blue-50 text-blue-900 shadow-sm"
                      : "border-slate-200 bg-white hover:border-slate-300 text-slate-800"
                  }`}
                >
                  <span className="font-semibold text-sm">{l.native}</span>
                  <span className="text-xs text-slate-500">{l.name}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="border-t border-slate-200 pt-5 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-semibold text-slate-900">
                  {t.preferences.alertsToggle}
                </div>
                <div className="text-xs text-slate-500">
                  Receive verified disease outbreak notifications for your locality.
                </div>
              </div>
              <input
                type="checkbox"
                checked={alertsEnabled}
                onChange={async (e) => {
                  const val = e.target.checked;
                  setAlertsEnabled(val);
                  if (token) {
                    await api.updatePreferences({ emergency_alerts_enabled: val }, token);
                    await refreshUser();
                  }
                }}
                className="w-5 h-5 accent-blue-600 rounded cursor-pointer"
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-semibold text-slate-900">
                  {t.preferences.locationToggle}
                </div>
                <div className="text-xs text-slate-500">
                  Enable high-precision triage and nearest facility lookup.
                </div>
              </div>
              <input
                type="checkbox"
                checked={locationEnabled}
                onChange={async (e) => {
                  const val = e.target.checked;
                  setLocationEnabled(val);
                  if (token) {
                    await api.updatePreferences({ location_sharing_enabled: val }, token);
                    await refreshUser();
                  }
                }}
                className="w-5 h-5 accent-blue-600 rounded cursor-pointer"
              />
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Emergency Contacts */}
      {activeTab === "emergency" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500 font-medium">
              Registered Contacts ({contacts.length})
            </span>
            {!showAddContact && (
              <Button size="sm" variant="outline" onClick={() => setShowAddContact(true)}>
                <Plus className="w-3.5 h-3.5 mr-1" />
                {t.profile.addContact}
              </Button>
            )}
          </div>

          {showAddContact && (
            <form onSubmit={handleAddContact} className="p-4 rounded-2xl border border-blue-200 bg-blue-50/50 space-y-3">
              <div className="text-xs font-bold text-blue-900 uppercase tracking-wider">
                New Emergency Contact
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <Input
                  label={t.profile.contactName}
                  value={contactName}
                  onChange={(e) => setContactName(e.target.value)}
                  placeholder="e.g. Ramesh"
                  required
                />
                <Input
                  label={t.profile.relationship}
                  value={contactRelation}
                  onChange={(e) => setContactRelation(e.target.value)}
                  placeholder="e.g. Spouse / Brother / Parent"
                  required
                />
              </div>
              <Input
                label={t.profile.phone}
                value={contactPhone}
                onChange={(e) => setContactPhone(e.target.value)}
                placeholder="+91 98765 00000"
                required
              />
              <div className="flex items-center justify-between pt-1">
                <label className="flex items-center gap-2 text-xs font-semibold text-slate-700 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={contactPrimary}
                    onChange={(e) => setContactPrimary(e.target.checked)}
                    className="w-4 h-4 accent-blue-600 rounded"
                  />
                  Mark as Primary Emergency Contact
                </label>
                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowAddContact(false)}
                  >
                    {t.common.cancel}
                  </Button>
                  <Button type="submit" size="sm" isLoading={isSaving}>
                    {t.common.save}
                  </Button>
                </div>
              </div>
            </form>
          )}

          {contacts.length === 0 && !showAddContact ? (
            <EmptyState
              icon={<Shield className="w-6 h-6 text-slate-400" />}
              title={t.profile.noContacts}
              description="Register at least one primary emergency contact to ensure immediate reachability."
              action={
                <Button size="sm" onClick={() => setShowAddContact(true)}>
                  {t.profile.addContact}
                </Button>
              }
            />
          ) : (
            <div className="space-y-2">
              {contacts.map((c) => (
                <div
                  key={c.id}
                  className="flex items-center justify-between p-3.5 rounded-xl border border-slate-200 bg-white hover:border-slate-300 transition-colors"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-sm text-slate-900">{c.name}</span>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-medium">
                        {c.relationship}
                      </span>
                      {c.is_primary && (
                        <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-800">
                          {t.profile.primaryBadge}
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-slate-500 mt-0.5 font-mono">{c.phone_number}</div>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleDeleteContact(c.id)}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                    title="Remove Contact"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </>
  );
}

export function ProfileModal() {
  const { user, isProfileModalOpen, setIsProfileModalOpen } = useAuth();
  const { t } = useLanguage();

  if (!isProfileModalOpen || !user) return null;

  return (
    <Modal
      isOpen={isProfileModalOpen}
      onClose={() => setIsProfileModalOpen(false)}
      title={t.profile.title}
      description={t.profile.subtitle}
      className="max-w-xl"
    >
      <ProfileModalContent
        key={user.id}
        user={user}
      />
    </Modal>
  );
}
