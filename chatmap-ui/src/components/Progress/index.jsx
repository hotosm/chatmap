import SlDialog from "@shoelace-style/shoelace/dist/react/dialog/index.js";
import SlProgressBar from '@shoelace-style/shoelace/dist/react/progress-bar/index.js';

export default function Progress({
  open, setOpen, left, total, children,
}) {
  return (
    <SlDialog
      open={open}
      onSlAfterHide={() => setOpen(false)}
    >
      <h2 slot="label" className="dialog__title">
        { children }
      </h2>

      <SlProgressBar value={(left / total) * 100} />
    </SlDialog>
  );
};
