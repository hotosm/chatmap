function QRCode({ img }) {
    return (
        <div className="connectForm">
            <div className="connectFormWrapper">
                <div>
                    <h2>
                        <FormattedMessage
                            id = "app.linked.linkYourDevice"
                            defaultMessage="Link your device"
                        />
                    </h2>
                    <h3>
                        <FormattedMessage
                            id = "app.linked.linkYourDevice.legend"
                            defaultMessage="Receive all your chat messages and convert them into a map"
                        />
                    </h3>
                    <ol>
                        <li>
                            <FormattedMessage
                                id = "app.linked.linkYourDevice.open"
                                defaultMessage="Open"
                            />
                            &nbsp;
                            <strong>WhatsApp</strong>
                            &nbsp;
                            <FormattedMessage
                                id = "app.linked.linkYourDevice.onYourPhone"
                                defaultMessage="on your phone"
                            />
                        </li>
                        <li>
                            <FormattedMessage
                                id = "app.linked.linkYourDevice.tap"
                                defaultMessage="Tap"
                            />
                            &nbsp;
                            <strong>
                            <FormattedMessage
                                id = "app.linked.linkYourDevice.menu"
                                defaultMessage="menu"
                            />
                            </strong>
                            &nbsp;
                            <FormattedMessage
                                id = "app.linked.linkYourDevice.onAndroidOr"
                                defaultMessage="on Android or"
                            />
                            &nbsp;
                            <strong>
                                <FormattedMessage
                                    id = "app.linked.linkYourDevice.settings"
                                    defaultMessage="settings"
                                />
                            </strong>
                            &nbsp;
                            <FormattedMessage
                                id = "app.linked.linkYourDevice.onIphone"
                                defaultMessage="on iPhone"
                            />
                        </li>
                        <li>
                            <FormattedMessage
                                id = "app.linked.linkYourDevice.tap"
                                defaultMessage="Tap"
                            />
                            &nbsp;
                            <strong>
                            <FormattedMessage
                                id = "app.linked.linkYourDevice.linkedDevices"
                                defaultMessage="Linked devices"
                            />
                            </strong>
                            &nbsp;
                            <FormattedMessage
                                id = "app.linked.linkYourDevice.then"
                                defaultMessage="then"
                            />
                            &nbsp;
                            <strong>
                                <FormattedMessage
                                    id = "app.linked.linkYourDevice.LinkDevice"
                                    defaultMessage="Link device"
                                />
                            </strong>
                        </li>
                        <li>Scan the QR code and start mapping!</li>
                    </ol>
                </div>
                <div>
                    <img className="qrCode" src={img} alt="QR Code" />
                </div>
            </div>
            <hr />
            <small>All your messages, including media, will be stored encrypted. Only locations and related content will be available for creating your map.
            </small>
        </div>
    )
}

export default QRCode;


