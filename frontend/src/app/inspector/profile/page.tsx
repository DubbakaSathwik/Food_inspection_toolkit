"use client";

import { ProfileView } from "@/components/profile-view";
import { PageHeader } from "@/components/shell";

export default function ProfilePage() {
  return (
    <>
      <PageHeader title="Profile" subtitle="Your account, role and inspection activity." />
      <ProfileView />
    </>
  );
}
