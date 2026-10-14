// The DriverGuard logo, one source for every page (14/10, the user's choice: the same as the login page,
// option 6 of the background mock-up): the shield mascot, and the name in two colours, "Driver" in the
// text colour and "Guard" in green.
import mascot from "../assets/mascot.png";

/** The shield mascot. Its size comes from the caller's class (.brand-mascot sets the default). */
export function BrandMark({ className = "" }: { className?: string }) {
  return <img className={`brand-mascot ${className}`} src={mascot} alt="" aria-hidden />;
}

/** "DriverGuard" with "Guard" in green; `plain` keeps both halves in the surrounding colour (the HUD at L3). */
export function BrandName({ plain = false }: { plain?: boolean }) {
  return (
    <>
      <span>Driver</span>
      <span className={plain ? undefined : "brand-name-2"}>Guard</span>
    </>
  );
}
