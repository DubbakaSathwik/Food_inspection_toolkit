"use client";

import { useState } from "react";
import { ApiError, errorMessage } from "@/lib/api";
import { SelectField, TextArea, TextField } from "./ui";

export type RefForm = {
  product_name: string;
  brand: string;
  variant: string;
  category: string;
  net_quantity: string;
  package_sizes: string;
  gtin: string;
  manufacturer: { name: string; registered_address: string; facility_address: string; state: string; district: string; contact: string };
  licence: { number: string; valid_from: string; valid_until: string; status: string; fbo_category: string };
  notes: string;
};

export function emptyRef(): RefForm {
  return {
    product_name: "",
    brand: "",
    variant: "",
    category: "staples",
    net_quantity: "",
    package_sizes: "",
    gtin: "",
    manufacturer: { name: "", registered_address: "", facility_address: "", state: "", district: "", contact: "" },
    licence: { number: "", valid_from: "", valid_until: "", status: "active", fbo_category: "" },
    notes: "",
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function fromRecord(r: any): RefForm {
  const e = emptyRef();
  return {
    ...e,
    ...Object.fromEntries(
      Object.keys(e)
        .filter((k) => typeof r?.[k] === "string")
        .map((k) => [k, r[k]]),
    ),
    package_sizes: (r?.package_sizes ?? []).join("; "),
    manufacturer: { ...e.manufacturer, ...(r?.manufacturer ?? {}) },
    licence: { ...e.licence, ...Object.fromEntries(Object.entries(r?.licence ?? {}).map(([k, v]) => [k, v ?? ""])) },
  } as RefForm;
}

export function toPayload(f: RefForm) {
  return {
    ...f,
    gtin: f.gtin.replace(/\D/g, ""),
    package_sizes: f.package_sizes
      .split(";")
      .map((s) => s.trim())
      .filter(Boolean),
    licence: {
      ...f.licence,
      number: f.licence.number.replace(/\D/g, ""),
      valid_from: f.licence.valid_from || null,
      valid_until: f.licence.valid_until || null,
    },
  };
}

/** Combined product + manufacturer + demo licence form (create and edit). */
export function ReferenceFormFields({
  value,
  onChange,
  errors,
}: {
  value: RefForm;
  onChange: (f: RefForm) => void;
  errors: Record<string, string>;
}) {
  const top = (k: keyof RefForm) => (e: { target: { value: string } }) => onChange({ ...value, [k]: e.target.value });
  const m = (k: keyof RefForm["manufacturer"]) => (e: { target: { value: string } }) =>
    onChange({ ...value, manufacturer: { ...value.manufacturer, [k]: e.target.value } });
  const l = (k: keyof RefForm["licence"]) => (e: { target: { value: string } }) =>
    onChange({ ...value, licence: { ...value.licence, [k]: e.target.value } });
  const g = "grid grid-cols-2 gap-3 max-[760px]:grid-cols-1";
  return (
    <div className="flex flex-col gap-5">
      <fieldset className="m-0 p-0 border-0">
        <legend className="font-bold mb-2">Product</legend>
        <div className={g}>
          <TextField
            label="Product name *"
            value={value.product_name}
            onChange={top("product_name")}
            error={errors.product_name}
            maxLength={200}
          />
          <TextField label="Brand *" value={value.brand} onChange={top("brand")} error={errors.brand} maxLength={200} />
          <TextField label="Variant" value={value.variant} onChange={top("variant")} maxLength={200} />
          <SelectField label="Category *" value={value.category} onChange={top("category")} error={errors.category}>
            <option value="beverages">Packaged beverages & water</option>
            <option value="snacks">Packaged snacks</option>
            <option value="dairy">Dairy products</option>
            <option value="staples">Groceries & food staples</option>
          </SelectField>
          <TextField label="Net quantity" value={value.net_quantity} onChange={top("net_quantity")} placeholder="500 g" />
          <TextField
            label="Package sizes (separate with ;)"
            value={value.package_sizes}
            onChange={top("package_sizes")}
            placeholder="500 g; 1 kg"
          />
          <TextField
            label="Barcode / GTIN"
            value={value.gtin}
            onChange={top("gtin")}
            error={errors.gtin}
            inputMode="numeric"
            maxLength={14}
          />
        </div>
      </fieldset>
      <fieldset className="m-0 p-0 border-0">
        <legend className="font-bold mb-2">Manufacturer</legend>
        <div className={g}>
          <TextField label="Company name" value={value.manufacturer.name} onChange={m("name")} />
          <TextField label="Contact" value={value.manufacturer.contact} onChange={m("contact")} />
          <TextArea label="Registered address" value={value.manufacturer.registered_address} onChange={m("registered_address")} />
          <TextArea label="Manufacturing facility address" value={value.manufacturer.facility_address} onChange={m("facility_address")} />
          <TextField label="State" value={value.manufacturer.state} onChange={m("state")} />
          <TextField label="District" value={value.manufacturer.district} onChange={m("district")} />
        </div>
      </fieldset>
      <fieldset className="m-0 p-0 border-0">
        <legend className="font-bold mb-2">FSSAI licence (demo record)</legend>
        <div className={g}>
          <TextField
            label="Licence / registration no. (14 digits)"
            value={value.licence.number}
            onChange={l("number")}
            error={errors["licence.number"]}
            inputMode="numeric"
          />
          <SelectField label="Status" value={value.licence.status} onChange={l("status")}>
            <option value="active">Active</option>
            <option value="expired">Expired</option>
            <option value="suspended">Suspended</option>
          </SelectField>
          <TextField label="Valid from" type="date" value={value.licence.valid_from} onChange={l("valid_from")} />
          <TextField label="Valid until" type="date" value={value.licence.valid_until} onChange={l("valid_until")} />
          <TextField
            label="Food business category"
            value={value.licence.fbo_category}
            onChange={l("fbo_category")}
            placeholder="Manufacturer"
          />
        </div>
      </fieldset>
      <TextArea label="Notes" value={value.notes} onChange={top("notes")} maxLength={2000} />
    </div>
  );
}

export function useRefSubmit() {
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  async function run<T>(fn: () => Promise<T>): Promise<T | null> {
    setBusy(true);
    setErr(null);
    setErrors({});
    try {
      return await fn();
    } catch (e) {
      if (e instanceof ApiError && e.fields) setErrors(e.fields);
      setErr(errorMessage(e));
      return null;
    } finally {
      setBusy(false);
    }
  }
  return { errors, err, busy, run };
}
