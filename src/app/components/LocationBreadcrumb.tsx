"use client";

import { memo } from "react";

type Props = {
  country: string;
  stateName: string | null;
  districtName: string | null;
  onNavigate: (level: "country" | "state") => void;
};

/**
 * Geographic context. Stays visible under the timeline so the user always knows
 * where in India the climate state applies while moving through time.
 */
function LocationBreadcrumb({ country, stateName, districtName, onNavigate }: Props) {
  const atCountry = !stateName || stateName.toUpperCase() === "INDIA";
  return (
    <nav className="crumb" aria-label="Geographic context">
      <button
        className={atCountry ? "crumb-node current" : "crumb-node"}
        onClick={() => onNavigate("country")}
        aria-current={atCountry ? "true" : undefined}
      >
        {country}
      </button>
      {!atCountry && (
        <>
          <span className="crumb-sep" aria-hidden="true">/</span>
          <button
            className={!districtName ? "crumb-node current" : "crumb-node"}
            onClick={() => onNavigate("state")}
            aria-current={!districtName ? "true" : undefined}
          >
            {stateName}
          </button>
        </>
      )}
      {districtName && (
        <>
          <span className="crumb-sep" aria-hidden="true">/</span>
          <span className="crumb-node current">{districtName}</span>
        </>
      )}
    </nav>
  );
}

export default memo(LocationBreadcrumb);
