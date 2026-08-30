import { useEffect, useRef } from 'react';
import { Receipt } from '../types';

const NON_TERMINAL_STATUSES = new Set([
  'UPLOADING',
  'PENDING',
  'PROCESSING',
  'OCR_PROCESSING',
  'EXTRACTING',
  'VALIDATING',
  'INDEXING',
]);

/**
 * Polls `onTick` every `intervalMs` while at least one receipt in the given
 * list is still being processed in the background (OCR/extraction/indexing),
 * so the UI picks up the finished result automatically. Stops as soon as
 * every receipt reaches a terminal status (COMPLETED / NEEDS_REVIEW / FAILED).
 */
export function useProcessingPoll(receipts: Receipt[], onTick: () => void, intervalMs = 3000) {
  const hasPending = receipts.some((r) => NON_TERMINAL_STATUSES.has(r.processing_status));
  const callbackRef = useRef(onTick);
  callbackRef.current = onTick;

  useEffect(() => {
    if (!hasPending) return;
    const id = setInterval(() => callbackRef.current(), intervalMs);
    return () => clearInterval(id);
  }, [hasPending, intervalMs]);
}
