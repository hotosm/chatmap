import Modal from 'react-modal';

Modal.setAppElement('#root');

function NavModal({ isOpen, afterOpen, onClose, content }) {

  const customStyles = {
    content: {
      top: '50%',
      left: '50%',
      right: 'auto',
      bottom: 'auto',
      marginRight: '-50%',
      transform: 'translate(-50%, -50%)',
      minWidth: '60vw',
      minHeight: '60vh',
      textAlign: 'center'
    },
  };

  return (
      <Modal
          isOpen={isOpen}
          onAfterOpen={afterOpen}
          onRequestClose={onClose}
          style={customStyles}
          contentLabel="Example Modal"
      >
          {content}
    </Modal>
  );
}

export default NavModal;


