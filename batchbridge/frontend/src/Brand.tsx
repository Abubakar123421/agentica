type BrandProps = {
  className?: string;
  markOnly?: boolean;
};

export function Brand({ className = "", markOnly = false }: BrandProps) {
  return (
    <span className={`brand ${className}`.trim()}>
      <img className="brand-mark" src="/brand/escalera-mark.svg" alt="" />
      {!markOnly && <span>Escalera</span>}
    </span>
  );
}
