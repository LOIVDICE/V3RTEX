import React from "react";
import { Button } from "./Button";

interface ModalProps {
  title: string;
  isOpen: boolean;
  onClose: () => void;
  onConfirm?: () => void;
  confirmLabel?: string;
  children: React.ReactNode;
}

export function Modal({ title, isOpen, onClose, onConfirm, confirmLabel = "Confirm", children }: ModalProps) {
  if (!isOpen) return null;
  return (
    <div className="modal-overlay">
      <div className="modal">
        <div className="modal-header">
          <h2>{title}</h2>
          <Button label="✕" onClick={onClose} variant="secondary" />
        </div>
        <div className="modal-body">{children}</div>
        {onConfirm && (
          <div className="modal-footer">
            <Button label="Cancel" onClick={onClose} variant="secondary" />
            <Button label={confirmLabel} onClick={onConfirm} variant="primary" />
          </div>
        )}
      </div>
    </div>
  );
}

export default Modal;
