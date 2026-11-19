"use client";

import { useEffect, useState } from "react";
import { apiBlob, api, publicUrl } from "@/lib/api";
import { Icon } from "./icon";

type SiteImages = Record<"hero" | "signin" | "banner", { url: string; alt: string } | null>;
let siteImagesPromise: Promise<SiteImages> | null = null;
export function refreshSiteImages() {
  siteImagesPromise = null;
}
function loadSiteImages(): Promise<SiteImages> {
  siteImagesPromise ??= api<SiteImages>("/api/v1/public/site-images", { auth: false }).catch(() => ({
    hero: null,
    signin: null,
    banner: null,
  }));
  return siteImagesPromise;
}

/** Labelled placeholder slot, replaced by the image uploaded in Admin › Settings › Website Images. */
export function ImageSlot({
  slot,
  label,
  className = "",
  style,
}: {
  slot: keyof SiteImages;
  label: string;
  className?: string;
  style?: React.CSSProperties;
}) {
  const [img, setImg] = useState<{ url: string; alt: string } | null | undefined>(undefined);
  useEffect(() => {
    let live = true;
    void loadSiteImages().then((s) => live && setImg(s[slot]));
    return () => {
      live = false;
    };
  }, [slot]);
  if (img) {
    return (
      // eslint-disable-next-line @next/next/no-img-element -- served by our API, dimensions vary
      <img
        src={publicUrl(img.url)}
        alt={img.alt || label}
        className={`object-cover ${className}`}
        style={{ borderRadius: 12, width: "100%", ...style }}
      />
    );
  }
  return (
    <div className={`cs-slot ${className}`} style={style} role="img" aria-label={`${label} (placeholder)`}>
      <Icon name="image" size={22} />
      <span style={{ maxWidth: 260 }}>{label}</span>
    </div>
  );
}

/** Fetches an authenticated binary (photo/PDF) and exposes an object URL. */
export function useBlobUrl(path: string | null): { url: string | null; error: boolean } {
  const [state, setState] = useState<{ url: string | null; error: boolean }>({ url: null, error: false });
  useEffect(() => {
    if (!path) return;
    let live = true;
    let created: string | null = null;
    apiBlob(path)
      .then((b) => {
        created = URL.createObjectURL(b);
        if (live) setState({ url: created, error: false });
      })
      .catch(() => live && setState({ url: null, error: true }));
    return () => {
      live = false;
      if (created) URL.revokeObjectURL(created);
    };
  }, [path]);
  return path ? state : { url: null, error: false };
}

export function AuthImage({
  path,
  alt,
  className = "",
  style,
}: {
  path: string | null;
  alt: string;
  className?: string;
  style?: React.CSSProperties;
}) {
  const { url, error } = useBlobUrl(path);
  if (!path || error) return <PackIllustration label={error ? "Photo unavailable" : alt} />;
  if (!url)
    return <div className="cs-skel" style={{ width: "100%", height: "100%", minHeight: 120, ...style }} aria-label="Loading photo" />;
  // eslint-disable-next-line @next/next/no-img-element -- blob URL from the authenticated API
  return <img src={url} alt={alt} className={`object-contain ${className}`} style={{ width: "100%", height: "100%", ...style }} />;
}

/** Demo-only CSS drawing of a product pack (shown when no real photo is available). */
export function PackIllustration({ label = "Product pack", back = false }: { label?: string; back?: boolean }) {
  return (
    <div
      role="img"
      aria-label={`${label} (illustration)`}
      className="relative grid place-items-center w-full h-full"
      style={{ background: "#F3EFE2", borderRadius: 10, minHeight: 120 }}
    >
      <div
        style={{
          width: "46%",
          aspectRatio: "3/4",
          borderRadius: 8,
          background: back ? "#FBF8F0" : "#C5D89D",
          border: "1.5px solid #9CAB84",
          display: "flex",
          flexDirection: "column",
          gap: 6,
          padding: 10,
          boxShadow: "0 6px 14px rgba(60,80,40,.12)",
        }}
      >
        <span style={{ height: 8, width: "70%", borderRadius: 4, background: back ? "#DCE3C6" : "#56703A" }} />
        <span style={{ height: 6, width: "50%", borderRadius: 4, background: "#9CAB84" }} />
        <span style={{ flex: 1, borderRadius: 6, background: back ? "#EEF2E1" : "#E3EACF" }} />
        <span style={{ height: 5, width: "80%", borderRadius: 3, background: "#9CAB84" }} />
      </div>
    </div>
  );
}
