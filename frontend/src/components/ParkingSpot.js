import React from 'react';

export default function ParkingSpot({ id, label, left, top, onClick, isSelected }) {
  const style = {
    left: `${left}%`,
    top: `${top}%`
  };

  return (
    <button
      className={`parking-spot ${isSelected ? 'selected' : ''}`}
      style={style}
      onClick={() => onClick(id)}
      aria-label={`Parking spot ${label}`}
    >
      {label}
    </button>
  );
}
