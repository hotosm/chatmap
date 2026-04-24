import SlDialog from "@shoelace-style/shoelace/dist/react/dialog/index.js";

export default function InfoMapDialog({
  open, setOpen, mapData
}) {
  return (
    <SlDialog
      open={open}
      onSlAfterHide={() => setOpen(false)}
    >
      <h2 slot="label" className="dialog__title">
        {mapData.name}
      </h2>
      <p>{mapData.description}</p>
    </SlDialog>
  );
};
