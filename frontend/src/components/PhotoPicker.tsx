import { useEffect, useId, useRef, useState } from "react";
import { ImagePlus, X } from "lucide-react";
import { checkImage } from "../lib/images";

export function PhotoPreview({
  file,
  alt,
  className,
}: {
  file: File;
  alt: string;
  className?: string;
}) {
  const imageRef = useRef<HTMLImageElement>(null);
  useEffect(() => {
    const next = URL.createObjectURL(file);
    if (imageRef.current) imageRef.current.src = next;
    return () => URL.revokeObjectURL(next);
  }, [file]);
  return <img ref={imageRef} className={className} alt={alt} />;
}

export function PhotoPicker({
  label,
  hint,
  file,
  onChange,
  required = false,
  disabled = false,
}: {
  label: string;
  hint: string;
  file?: File;
  onChange: (file: File | undefined) => void;
  required?: boolean;
  disabled?: boolean;
}) {
  const id = useId();
  const [error, setError] = useState("");
  const [checking, setChecking] = useState(false);
  const generation = useRef(0);
  useEffect(
    () => () => {
      generation.current++;
    },
    [],
  );
  async function select(file: File | undefined) {
    if (!file) return;
    const current = ++generation.current;
    setChecking(true);
    setError("");
    try {
      await checkImage(file);
      if (current === generation.current) onChange(file);
    } catch (reason) {
      if (current === generation.current)
        setError(
          reason instanceof Error ? reason.message : "사진을 확인해 주세요.",
        );
    } finally {
      if (current === generation.current) setChecking(false);
    }
  }
  return (
    <div className="photo-field">
      <div className="field-title">
        <span>{label}</span>
        <span className={required ? "required-tag" : "optional-tag"}>
          {required ? "필수" : "선택"}
        </span>
      </div>
      <label
        className={`photo-picker ${file ? "has-photo" : ""}`}
        htmlFor={id}
        onDragOver={(event) => {
          event.preventDefault();
        }}
        onDrop={(event) => {
          event.preventDefault();
          if (disabled) return;
          if (event.dataTransfer.files.length !== 1) {
            setError("한 칸에는 사진 한 장만 추가해 주세요.");
            return;
          }
          void select(event.dataTransfer.files[0]);
        }}
      >
        {file ? (
          <PhotoPreview file={file} alt={`${label} 미리보기`} />
        ) : (
          <>
            <ImagePlus size={27} strokeWidth={1.4} />
            <strong>{checking ? "사진 확인 중…" : "사진 선택"}</strong>
            <span>{hint}</span>
          </>
        )}
        <input
          id={id}
          type="file"
          disabled={disabled}
          accept="image/jpeg,image/png,image/webp"
          aria-label={label}
          aria-describedby={error ? `${id}-error` : undefined}
          onChange={(event) => {
            void select(event.target.files?.[0]);
            event.target.value = "";
          }}
        />
      </label>
      {file ? (
        <div className="file-caption">
          <span>{file.name}</span>
          <button
            type="button"
            disabled={disabled}
            className="icon-button"
            aria-label={`${label} 제거`}
            onClick={() => {
              generation.current++;
              setChecking(false);
              setError("");
              onChange(undefined);
            }}
          >
            <X size={16} />
          </button>
        </div>
      ) : null}
      {error ? (
        <p className="error" role="alert" id={`${id}-error`}>
          {error}
        </p>
      ) : null}
    </div>
  );
}
