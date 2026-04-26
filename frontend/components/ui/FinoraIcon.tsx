interface Props {
  size?: number;
  className?: string;
}

export function FinoraIcon({ size = 24, className = "" }: Props) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="Finora"
    >
      {/*
        Gemini-style 4-pointed star:
        Two overlapping ellipses rotated 90° — creates the characteristic
        pinched-diamond sparkle shape. Filled with currentColor so it
        inherits text color from parent.
      */}
      <path
        d="M12 2C12 2 13.5 7.5 18 12C13.5 16.5 12 22 12 22C12 22 10.5 16.5 6 12C10.5 7.5 12 2 12 2Z"
        fill="currentColor"
        opacity="1"
      />
      <path
        d="M2 12C2 12 7.5 10.5 12 6C16.5 10.5 22 12 22 12C22 12 16.5 13.5 12 18C7.5 13.5 2 12 2 12Z"
        fill="currentColor"
        opacity="0.6"
      />
    </svg>
  );
}
