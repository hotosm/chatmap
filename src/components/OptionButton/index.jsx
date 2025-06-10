function OptionButton({ value, left, right, active, onClick }) {

  return (
    <button 
        className={[
                "optionButton",
                right ? "optionButtonRight" : "",
                left ? "optionButtonLeft" : "",
                active ? "optionButtonActive" : "",
            ].join(" ")
        }
        onClick={() => onClick()}
    >{value}</button>
  );
}

export default OptionButton;
