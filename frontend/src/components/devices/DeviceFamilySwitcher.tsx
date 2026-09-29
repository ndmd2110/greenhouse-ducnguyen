// frontend/src/components/devices/DeviceFamilySwitcher.tsx
import React from "react";
import type { DeviceFamily } from "../../services/api";

interface DeviceFamilySwitcherProps {
  selectedFamily: DeviceFamily;
  onSelectFamily: (family: DeviceFamily) => void;
}

export const DeviceFamilySwitcher: React.FC<DeviceFamilySwitcherProps> = ({
  selectedFamily,
  onSelectFamily,
}) => {
  const families: DeviceFamily[] = ["simulation", "edge"];

  return (
    <div className="inline-flex rounded-lg border border-gray-200 p-1 bg-gray-50">
      {families.map((fam) => {
        const isActive = selectedFamily === fam;
        return (
          <button
            key={fam}
            onClick={() => onSelectFamily(fam)}
            className={`px-3 py-1.5 text-sm font-medium rounded-md capitalize transition-all ${
              isActive
                ? "bg-white text-gray-900 shadow-sm font-semibold"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {fam}
          </button>
        );
      })}
    </div>
  );
};