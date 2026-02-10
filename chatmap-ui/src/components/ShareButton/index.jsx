import { FormattedMessage } from 'react-intl';
import useAPI from '../../components/ChatMap/useApi.js'

function ShareButton({ sharing }) {

  const {
    updateMapShare,
    mapShare
  } = useAPI();

  const handleClick = async () => {
    await updateMapShare();
  };

  return (
    <sl-button
      variant="primary"
      size="small"
      onClick={handleClick}
    >
      <FormattedMessage
        id = "app.share"
        defaultMessage={mapShare.sharing || sharing || "Share"}
      />
      <sl-icon name="link" slot="prefix"></sl-icon>
    </sl-button>
  );
}

export default ShareButton;
