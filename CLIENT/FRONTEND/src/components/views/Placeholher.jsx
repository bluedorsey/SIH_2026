import React from 'react';

export default function PlaceholderView({ title }) {
  return (
    <main className="flex-1 p-8">
      <div className="rounded-xl border border-dashed border-gray-300 bg-white p-12 text-center shadow-xs">
        <h2 className="text-xl font-bold capitalize text-gray-800">{title}</h2>
        <p className="mt-2 text-sm text-gray-500">
          Content for the <span className="font-semibold">{title}</span> section is under construction.
        </p>
      </div>
    </main>
  );
}