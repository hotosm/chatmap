import { FormattedMessage } from 'react-intl';
import useAPI from '../../components/ChatMap/useApi.js'

function ShareButton({ sharing, id }) {

  const {
    updateMapShare,
    mapShare,
  } = useAPI();

  const handleClick = async () => {
    await updateMapShare(id);
  };
  const sharingStatus = mapShare.sharing || sharing;
  return (
    <sl-button
      variant="primary"
      size="small"
      onClick={handleClick}
    >
      <FormattedMessage id={"app.maps.sharing." + sharingStatus} />
      <sl-icon name={sharingStatus === "private" ? "lock" : "link"} slot="prefix"></sl-icon>
    </sl-button>
  );
}

export default ShareButton;
