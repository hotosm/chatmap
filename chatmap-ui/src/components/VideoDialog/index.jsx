import SlDialog from "@shoelace-style/shoelace/dist/react/dialog/index.js";

export default function VideoDialog({
  url, open, setOpen
}) {

  return (
    <SlDialog
      open={open}
      onSlAfterHide={() => setOpen(false)}
      className="dialog__video"
    >
        <video src={url} autoPlay controls />
    </SlDialog>
  );
};
