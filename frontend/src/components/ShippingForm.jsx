import { useState } from "react";

const initialState = {
  origin_zip: "",
  destination_zip: "",
  delivery_days: 3,
  weight_lbs: "",
  length_in: "",
  width_in: "",
  height_in: "",
};

function Field({ label, name, placeholder, type = "text", unit, value, hasError, onChange, errorMessage }) {
  return (
    <div className="field">
      <label className="field-label">{label}</label>
      <div className="field-input-wrap">
        <input
          className={`field-input ${hasError ? "field-input--error" : ""}`}
          type={type}
          name={name}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          step={type === "number" ? "0.1" : undefined}
          min={type === "number" ? "0.1" : undefined}
        />
        {unit && <span className="field-unit">{unit}</span>}
      </div>
      {errorMessage && <span className="field-error">{errorMessage}</span>}
    </div>
  );
}

export default function ShippingForm({ onSubmit, loading }) {
  const [form, setForm] = useState(initialState);
  const [errors, setErrors] = useState({});

  const validate = () => {
    const e = {};
    if (!/^\d{5}$/.test(form.origin_zip)) e.origin_zip = "Enter a valid 5-digit ZIP";
    if (!/^\d{5}$/.test(form.destination_zip)) e.destination_zip = "Enter a valid 5-digit ZIP";
    if (!form.weight_lbs || form.weight_lbs <= 0) e.weight_lbs = "Required";
    if (!form.length_in || form.length_in <= 0) e.length_in = "Required";
    if (!form.width_in || form.width_in <= 0) e.width_in = "Required";
    if (!form.height_in || form.height_in <= 0) e.height_in = "Required";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handle = (e) => {
    const { name, value } = e.target;
    setForm((f) => ({ ...f, [name]: value }));
    if (errors[name]) setErrors((err) => ({ ...err, [name]: null }));
  };

  const submit = (e) => {
    e.preventDefault();
    if (!validate()) return;
    onSubmit({
      origin_zip: form.origin_zip,
      destination_zip: form.destination_zip,
      delivery_days: parseInt(form.delivery_days),
      weight_lbs: parseFloat(form.weight_lbs),
      length_in: parseFloat(form.length_in),
      width_in: parseFloat(form.width_in),
      height_in: parseFloat(form.height_in),
    });
  };

  return (
    <form className="shipping-form" onSubmit={submit}>
      {/* Addresses */}
      <section className="form-section">
        <h2 className="section-title">
          <span className="section-icon">📍</span> Addresses
        </h2>
        <div className="form-row">
          <Field
            label="Origin ZIP Code"
            name="origin_zip"
            placeholder="e.g. 76201"
            value={form.origin_zip}
            hasError={Boolean(errors.origin_zip)}
            onChange={handle}
            errorMessage={errors.origin_zip}
          />
          <Field
            label="Destination ZIP Code"
            name="destination_zip"
            placeholder="e.g. 45152"
            value={form.destination_zip}
            hasError={Boolean(errors.destination_zip)}
            onChange={handle}
            errorMessage={errors.destination_zip}
          />
        </div>
      </section>

      {/* Delivery deadline */}
      <section className="form-section">
        <h2 className="section-title">
          <span className="section-icon">📅</span> Delivery Deadline
        </h2>
        <div className="field">
          <label className="field-label">
            Deliver within <strong className="accent-num">{form.delivery_days}</strong> business day{form.delivery_days > 1 ? "s" : ""}
          </label>
          <input
            type="range"
            name="delivery_days"
            min="1"
            max="10"
            value={form.delivery_days}
            onChange={handle}
            className="range-slider"
          />
          <div className="range-labels">
            <span>1 day</span>
            <span>10 days</span>
          </div>
        </div>
      </section>

      {/* Package */}
      <section className="form-section">
        <h2 className="section-title">
          <span className="section-icon">📦</span> Package Details
        </h2>
        <div className="form-row">
          <Field
            label="Weight"
            name="weight_lbs"
            placeholder="2.0"
            type="number"
            unit="lbs"
            value={form.weight_lbs}
            hasError={Boolean(errors.weight_lbs)}
            onChange={handle}
            errorMessage={errors.weight_lbs}
          />
        </div>
        <div className="form-row form-row--3">
          <Field
            label="Length"
            name="length_in"
            placeholder="12"
            type="number"
            unit="in"
            value={form.length_in}
            hasError={Boolean(errors.length_in)}
            onChange={handle}
            errorMessage={errors.length_in}
          />
          <Field
            label="Width"
            name="width_in"
            placeholder="8"
            type="number"
            unit="in"
            value={form.width_in}
            hasError={Boolean(errors.width_in)}
            onChange={handle}
            errorMessage={errors.width_in}
          />
          <Field
            label="Height"
            name="height_in"
            placeholder="6"
            type="number"
            unit="in"
            value={form.height_in}
            hasError={Boolean(errors.height_in)}
            onChange={handle}
            errorMessage={errors.height_in}
          />
        </div>
      </section>

      <button className="submit-btn" type="submit" disabled={loading}>
        {loading ? (
          <><span className="btn-spinner" /> Querying Agents...</>
        ) : (
          <>✦ Compare Shipping Rates</>
        )}
      </button>
    </form>
  );
}
