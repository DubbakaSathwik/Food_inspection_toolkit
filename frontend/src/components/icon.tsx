import { ICONS, type IconName, TAB_ICONS, type TabIconName } from "./icon-paths";

type Props = { name: IconName; size?: number; className?: string; color?: string; title?: string };

/** Monochrome outline icons from the design (24×24, stroke 1.6). Static trusted markup only. */
export function Icon({ name, size = 18, className, color, title }: Props) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color ?? "currentColor"}
      strokeWidth={1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden={title ? undefined : true}
      role={title ? "img" : undefined}
      aria-label={title}
      className={className}
      style={{ flexShrink: 0 }}
      dangerouslySetInnerHTML={{ __html: ICONS[name] }}
    />
  );
}

export function TabIcon({ name }: { name: TabIconName }) {
  return (
    <svg
      width={22}
      height={22}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.7}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      dangerouslySetInnerHTML={{ __html: TAB_ICONS[name] }}
    />
  );
}

export type { IconName };
