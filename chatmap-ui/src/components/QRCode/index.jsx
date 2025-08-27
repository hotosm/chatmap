function QRCode({ img }) {
    return (
        <div className="connectForm">
            <div className="connectFormWrapper">
                <div>
                    <h2>Link your device</h2>
                    <h3>Receive all your chat messages and convert them into a map</h3>
                    <ol>
                        <li>Open <strong>WhatsApp</strong> on your phone</li>
                        <li>Tap <strong>Menu</strong> on Android or <strong>Settings</strong> on iPhone</li>
                        <li>Tap <strong>Linked devices</strong> then <strong>Link device</strong></li>
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


